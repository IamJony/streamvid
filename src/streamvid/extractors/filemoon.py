#!/usr/bin/env python3
# Extractor para filemoon, sfastwish, byse by IamJony

import sys
import re
import json
import base64
import hashlib
from urllib.parse import urlparse

from requests_html import HTMLSession
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from real_headers import real_headers

from ..unpacker import unpack_eval_script


# Helpers base64url / AES

def _b64url_decode(s: str) -> bytes:
    """Decodifica base64url sin padding."""
    if not s:
        return b""
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _qa():
    """Qa() del JS: {str(n): [n, 31-n]} para n=1..20."""
    return {str(n): [n, 31 - n] for n in range(1, 21)}


def _ea(version, length):
    """Reconstrucción de Ea(version, length) del JS de Byse.

    o = Qa()[version]  → [v, 31-v]
    Genera una secuencia 1-based alternando desde v y 31-v hacia fuera.
    """
    version_str = str(version).strip() if version is not None else ""
    o = _qa().get(version_str)
    if not o:
        return []
    o0, o1 = o
    order = [o0, o1]
    i = 1
    while len(order) < length:
        a, b = o0 + i, o1 - i
        if 1 <= a <= length and a not in order:
            order.append(a)
        if 1 <= b <= length and b not in order:
            order.append(b)
        i += 1
        if i > length * 2:
            break
    for k in range(1, length + 1):
        if k not in order:
            order.append(k)
    return order[:length]


def _ws(playback):
    """Reordena key_parts según Ea(version, length)."""
    parts = playback.get("key_parts") or []
    if not isinstance(parts, list):
        return []
    order = _ea(playback.get("version"), len(parts))
    if not order:
        return parts
    out = []
    for idx in order:
        if 1 <= idx <= len(parts):
            p = parts[idx - 1]
            if isinstance(p, str) and p:
                out.append(p)
    return out or parts


def _decrypt_byse_playback(playback: dict):
    """Descifra el payload AES-256-GCM de la API Byse.

    Reordena key_parts con Ea(version, len), decodifica b64url, concatena
    y prueba varias derivaciones de clave (join[:32], sha256, etc.).
    Devuelve (dict, nombre_clave) o (None, None).
    """
    parts_ordered = _ws(playback)
    if not parts_ordered:
        return None, None

    decoded = [_b64url_decode(p) for p in parts_ordered if p]
    decoded = [d for d in decoded if d]
    if not decoded:
        return None, None

    joined = b"".join(decoded)
    candidates = []

    if len(joined) >= 32:
        candidates.append(("join[:32]", joined[:32]))
    if len(decoded) >= 2 and all(len(d) == 16 for d in decoded[:2]):
        candidates.append(("parts[0]+parts[1]", decoded[0] + decoded[1]))
    if len(decoded[0]) == 32:
        candidates.append(("parts[0]", decoded[0]))
    candidates.append(("sha256(join)", hashlib.sha256(joined).digest()))
    candidates.append(("sha256(join|)", hashlib.sha256("|".join(parts_ordered).encode()).digest()))

    for iv_prop, payload_prop in (("iv", "payload"), ("iv2", "payload2")):
        iv_str = playback.get(iv_prop)
        payload_str = playback.get(payload_prop)
        if not iv_str or not payload_str:
            continue
        try:
            iv = _b64url_decode(iv_str)
            ciphertext = _b64url_decode(payload_str)
        except Exception:
            continue

        for name, key in candidates:
            if len(key) != 32:
                continue
            try:
                aesgcm = AESGCM(key)
                plaintext = aesgcm.decrypt(iv, ciphertext, None)
                return json.loads(plaintext.decode("utf-8")), name
            except Exception:
                continue

    return None, None


def _extract_best_source_url(data: dict):
    """Del JSON descifrado, saca la mejor URL (mayor height)."""
    sources = data.get("sources")
    if isinstance(sources, list) and sources:
        best_url, best_height = None, -1
        for src in sources:
            url = src.get("url") or src.get("file")
            height = src.get("height", 0) or 0
            if url and isinstance(height, int) and height >= best_height:
                best_url, best_height = url, height
        if best_url:
            return best_url
    for k in ("source", "file", "url"):
        v = data.get(k)
        if isinstance(v, str) and v:
            return v
    return None


class FileMoonExtractor:
    """Clase para extraer videos de FileMoon / Byse"""

    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug
        self.headers = None

    # ---------- API pública ----------

    def soporta(self, url):
        dominios = ("filemoon", "sfastwish", "flaswish",
                    "bysedikamoum", "n1mwq", "byse")
        return any(d in url.lower() for d in dominios)

    def extraer(self, url):
        # 1) API Byse moderna
        try:
            video_link = self._extraer_via_api_byse(url)
            if video_link:
                self._log(f"extracción API Byse OK: {video_link}", "ok")
                return video_link
        except Exception as e:
            self._log(f"API Byse falló: {e}", "warn")

        # 2) Fallback legacy (unpack eval)
        try:
            html = self._obtener_html(url)
            script = self._buscar_script_eval(html)
            if not script:
                raise Exception("No se encontró el script con eval")

            unpacked = unpack_eval_script(script, debug=self.debug)
            if not unpacked:
                raise Exception("eval-unpacker no pudo desempaquetar el script")

            video_link = self._extraer_video_link(unpacked)
            if not video_link:
                raise Exception("No se pudo encontrar el enlace del video")

            self._log(f"extracción legacy completada: {video_link}", "ok")
            return video_link
        except Exception as e:
            self._log(f"error fatal: {e}", "fail")
            raise

    def extraer_y_mostrar(self, url):
        try:
            video_link = self.extraer(url)
            print(video_link)
            return video_link
        except Exception as e:
            if self.debug:
                print(f"[filemoon] error: {e}", file=sys.stderr)
            sys.exit(1)

    def obtener_headers(self):
        return dict(self.headers) if self.headers else None

    # Logging

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[filemoon] {icons.get(level, '·')} {msg}", file=sys.stderr)

    # HTTP

    def _obtener_html(self, url):
        self._log(f"descargando: {url}", "step")
        try:
            headers = real_headers()
            response = self.session.get(url, headers=headers, allow_redirects=True)
            response.raise_for_status()
            self._log(f"HTML obtenido ({len(response.text)} bytes)", "ok")

            self.headers = dict(headers)
            self.headers["Referer"] = self._dominio_base(response.url)
            return response.text
        except Exception as e:
            self._log(f"error de descarga: {e}", "fail")
            raise Exception(f"Error al descargar la página: {e}")

    @staticmethod
    def _dominio_base(url):
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}/"

    @staticmethod
    def _extraer_code(url):
        m = re.search(r"/[de]/(?P<code>[a-zA-Z0-9]+)", url or "")
        return m.group("code") if m else None

    # API Byse 

    def _extraer_via_api_byse(self, url):
        """Intenta la API /api/videos/{code} de Byse y descifra el playback."""
        code = self._extraer_code(url)
        if not code:
            self._log("no se pudo extraer el code de la URL", "warn")
            return None

        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        api_url = f"{base}/api/videos/{code}"
        self._log(f"probando API Byse: {api_url}", "step")

        headers = real_headers()
        headers["Referer"] = base + "/"
        headers["Origin"] = base
        try:
            resp = self.session.get(api_url, headers=headers, allow_redirects=True)
            if resp.status_code != 200:
                self._log(f"API devolvió {resp.status_code}", "warn")
                return None
            data = resp.json()
        except Exception as e:
            self._log(f"error consultando API: {e}", "warn")
            return None

        playback = data.get("playback")
        if not playback:
            self._log("respuesta sin 'playback'", "warn")
            return None

        self._log(f"playback recibido (alg={playback.get('algorithm')}, "
                  f"v={playback.get('version')})", "ok")
        decrypted, key_name = _decrypt_byse_playback(playback)
        if decrypted is None:
            self._log("no se pudo descifrar el playback", "warn")
            return None
        self._log(f"playback descifrado con clave: {key_name}", "ok")

        best = _extract_best_source_url(decrypted)
        if best:
            self._log(f"URL de stream: {best}", "ok")
            return best
        self._log("JSON descifrado sin URL utilizable", "warn")
        return None

    # Parsing legacy

    def _buscar_script_eval(self, html):
        self._log("buscando script con eval(function...)", "step")
        script_pattern = (
            r'<script[^>]*type=[\'"]text/javascript[\'"][^>]*>'
            r'.*?eval\(function\(p,a,c,k,e,d\).*?</script>'
        )
        script_match = re.search(script_pattern, html, re.DOTALL | re.IGNORECASE)
        if script_match:
            self._log("script eval encontrado", "ok")
            return script_match.group()
        self._log("no se encontró script eval", "warn")
        return None

    def _extraer_video_link(self, texto):
        self._log("buscando enlace m3u8 en el texto", "step")
        master_pattern = r'(https?://[^"\'\s]+master\.m3u8[^"\'\s]*)'
        m = re.search(master_pattern, texto)
        if m:
            self._log(f"master.m3u8 encontrado: {m.group(1)}", "ok")
            return m.group(1)

        m3u8_pattern = r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)'
        m = re.search(m3u8_pattern, texto)
        if m:
            self._log(f".m3u8 alternativo encontrado: {m.group(1)}", "ok")
            return m.group(1)

        self._log("no se encontró ningún .m3u8", "warn")
        return None


def _main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    debug = "--debug" in sys.argv or "-d" in sys.argv

    if not args:
        if debug:
            print("Error: URL no proporcionada", file=sys.stderr)
            print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    extractor = FileMoonExtractor(debug=debug)
    extractor.extraer_y_mostrar(args[0])


if __name__ == "__main__":
    _main()
