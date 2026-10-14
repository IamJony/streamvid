#!/usr/bin/env python3
"""
Utiliza Streamvid para extraer y reproducir con el reproductor disponible.
Soporta Linux, macOS y Windows.

Uso:
    python scripts/play.py <url>
    python scripts/play.py <url> --player=mpv
    python scripts/play.py <url> --player=vlc
    python scripts/play.py <url> --no-play
    python scripts/play.py --list
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from streamvid import EXTRACTORS


# ---------- Detección de reproductores por SO ----------

def _candidatos(nombre):
    """Devuelve los posibles ejecutables para un reproductor según el SO."""
    if sys.platform == "win32":
        return {
            "mpv":  ["mpv.exe", "mpv"],
            "vlc":  ["vlc.exe", r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                     r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"],
            "mplayer": ["mplayer.exe", "mplayer"],
        }.get(nombre, [nombre])
    elif sys.platform == "darwin":  # macOS
        return {
            "mpv":  ["mpv", "/Applications/mpv.app/Contents/MacOS/mpv"],
            "vlc":  ["vlc", "/Applications/VLC.app/Contents/MacOS/VLC"],
            "iina": ["iina"],
        }.get(nombre, [nombre])
    else:  # Linux y otros Unix
        return {
            "mpv":  ["mpv"],
            "vlc":  ["vlc"],
            "cvlc": ["cvlc"],
            "mplayer": ["mplayer"],
        }.get(nombre, [nombre])


def _encontrar_ejecutable(nombre):
    """Devuelve la ruta al ejecutable o None si no está instalado."""
    for candidato in _candidatos(nombre):
        if os.path.isabs(candidato):
            if os.path.isfile(candidato):
                return candidato
        else:
            ruta = shutil.which(candidato)
            if ruta:
                return ruta
    return None


REPRODUCTORES = ["mpv", "vlc", "cvlc", "iina", "mplayer"]


def detectar_reproductor():
    """Devuelve (nombre, ruta) del primer reproductor instalado."""
    for nombre in REPRODUCTORES:
        ruta = _encontrar_ejecutable(nombre)
        if ruta:
            return nombre, ruta
    return None, None


def listar_reproductores():
    """Imprime qué reproductores están instalados."""
    print(f"Sistema: {sys.platform}")
    print(f"Reproductores instalados:\n")
    for nombre in REPRODUCTORES:
        ruta = _encontrar_ejecutable(nombre)
        marca = "✓" if ruta else "✗"
        extra = f"  ({ruta})" if ruta else ""
        print(f"  {marca} {nombre}{extra}")


# ---------- Extracción ----------

def extraer(url):
    """Prueba cada extractor hasta encontrar el que soporte la URL."""
    for cls in EXTRACTORS:
        extractor = cls()
        try:
            if not extractor.soporta(url):
                continue
        except AttributeError:
            continue

        print(f"[+] Usando extractor: {cls.__name__}")
        link = extractor.extraer(url)
        headers = None
        if hasattr(extractor, "obtener_headers"):
            headers = extractor.obtener_headers()
        return cls.__name__, link, headers

    raise RuntimeError(f"Ningún extractor reconoce la URL: {url}")


# ---------- Reproducción ----------

def reproducir_mpv(ruta, link, headers):
    """mpv acepta --user-agent y --referrer por CLI."""
    cmd = [ruta]
    if headers:
        ua = headers.get("User-Agent")
        ref = headers.get("Referer")
        if ua:
            cmd.append(f"--user-agent={ua}")
        if ref:
            cmd.append(f"--referrer={ref}")
    cmd.append(link)

    print(f"[+] Lanzando mpv...")
    subprocess.run(cmd)


def reproducir_vlc(ruta, link, headers, headless=False):
    """
    VLC no acepta --referrer por CLI. Se genera un .m3u temporal con
    las opciones embebidas y se fuerza el autoplay con --play-and-exit.
    """
    fd, m3u_path = tempfile.mkstemp(suffix=".m3u", prefix="streamvid_")
    os.close(fd)

    ref = (headers or {}).get("Referer", "")
    ua = (headers or {}).get("User-Agent", "")

    lineas = ["#EXTM3U"]
    if ref:
        lineas.append(f"#EXTVLCOPT:http-referrer={ref}")
    if ua:
        lineas.append(f"#EXTVLCOPT:http-user-agent={ua}")
    lineas.append(link)

    Path(m3u_path).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"[+] Playlist temporal: {m3u_path}")

    # --play-and-exit: arranca la reproducción al abrir
    # --started-from-file: evita la ventana vacía inicial
    cmd = [ruta, "--play-and-exit", "--started-from-file", m3u_path]

    print(f"[+] Lanzando VLC...")
    subprocess.run(cmd)


def reproducir_iina(ruta, link, headers):
    """IINA (macOS) acepta --mpv-* para pasar opciones a mpv."""
    cmd = [ruta]
    if headers:
        ua = headers.get("User-Agent")
        ref = headers.get("Referer")
        if ua:
            cmd.extend(["--mpv-user-agent", ua])
        if ref:
            cmd.extend(["--mpv-referrer", ref])
    cmd.append(link)

    print(f"[+] Lanzando IINA...")
    subprocess.run(cmd)


def reproducir_mplayer(ruta, link, headers):
    """mplayer usa -referer (una sola r) y los flags van antes del link."""
    cmd = [ruta]
    if headers:
        ua = headers.get("User-Agent")
        ref = headers.get("Referer")
        if ua:
            cmd.extend(["-user-agent", ua])
        if ref:
            cmd.extend(["-referer", ref])
    cmd.append(link)

    print(f"[+] Lanzando mplayer...")
    subprocess.run(cmd)


REPRODUCIR_FN = {
    "mpv":      reproducir_mpv,
    "vlc":      reproducir_vlc,
    "cvlc":     reproducir_vlc,
    "iina":     reproducir_iina,
    "mplayer":  reproducir_mplayer,
}


def reproducir(nombre, ruta, link, headers):
    fn = REPRODUCIR_FN.get(nombre)
    if not fn:
        raise RuntimeError(f"Reproductor no soportado: {nombre}")
    fn(ruta, link, headers)


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(
        description="Extrae un link de Streamvid y lo reproduce con mpv/VLC.",
    )
    parser.add_argument("url", nargs="?", help="URL del video")
    parser.add_argument("--player", choices=REPRODUCTORES,
                        help="Forzar un reproductor concreto")
    parser.add_argument("--list", action="store_true",
                        help="Listar reproductores disponibles y salir")
    parser.add_argument("--no-play", action="store_true",
                        help="Solo extraer, no reproducir")
    args = parser.parse_args()

    if args.list:
        listar_reproductores()
        return 0

    if not args.url:
        parser.print_help()
        return 1

    # 1. Extraer
    try:
        clase, link, headers = extraer(args.url)
    except Exception as e:
        print(f"[!] Error al extraer: {e}", file=sys.stderr)
        return 1

    print()
    print(f"Link:    {link}")
    if headers:
        for k, v in headers.items():
            print(f"  {k}: {v}")
    print()

    if args.no_play:
        return 0

    # 2. Elegir reproductor
    if args.player:
        ruta = _encontrar_ejecutable(args.player)
        if not ruta:
            print(f"[!] '{args.player}' no está instalado.", file=sys.stderr)
            return 1
        nombre = args.player
    else:
        nombre, ruta = detectar_reproductor()
        if not nombre:
            print("[!] No hay ningún reproductor compatible instalado.", file=sys.stderr)
            print("    Instala mpv o VLC:", file=sys.stderr)
            print("      Linux:  sudo apt install mpv", file=sys.stderr)
            print("      macOS:  brew install mpv", file=sys.stderr)
            print("      Windows: winget install mpv   (o descarga desde mpv.io)", file=sys.stderr)
            return 1

    print(f"[+] Reproduciendo con {nombre} ({ruta}) ...")

    # 3. Reproducir
    try:
        reproducir(nombre, ruta, link, headers)
    except Exception as e:
        print(f"[!] Error al reproducir: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
