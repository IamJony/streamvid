#!/usr/bin/env python3
# Extractor para mp4upload by IamJony

import sys
import re
from requests_html import HTMLSession
from real_headers import real_headers

# Headers y User-agent aletorios
random_headers = real_headers()


class MP4UploadExtractor:
    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[mp4upload] {icons.get(level, '·')} {msg}", file=sys.stderr)

    def procesar_url(self, url):
        self._log(f"procesando URL: {url}", "step")

        m = re.match(r'^https?://[^/]+/([a-zA-Z0-9]+)$', url)
        if m:
            embed = f"https://www.mp4upload.com/embed-{m.group(1)}.html"
            self._log(f"URL convertida a embed: {embed}", "ok")
            return embed

        if re.search(r'embed-([a-zA-Z0-9]+)', url):
            self._log("ya era URL embed", "ok")
            return url

        self._log("URL no válida para mp4upload", "fail")
        raise ValueError("URL no válida para mp4upload")

    def obtener_contenido(self, url):
        self._log(f"descargando: {url}", "step")
        try:
            response = self.session.get(url, headers=random_headers)
            response.raise_for_status()
            self._log(f"HTML obtenido ({len(response.text)} bytes)", "ok")
            return response.text
        except Exception as e:
            self._log(f"error de descarga: {e}", "fail")
            raise Exception(f"Error al descargar la página: {e}")

    def extraer_video_src(self, contenido):
        extractores = [
            self._extraer_src_javascript,
            self._extraer_eval_unpack,
            self._extraer_mp4_directo
        ]

        for extractor in extractores:
            nombre = extractor.__name__
            self._log(f"probando patrón: {nombre}", "step")
            try:
                video_link = extractor(contenido)
                if video_link:
                    self._log(f"patrón '{nombre}' encontró: {video_link}", "ok")
                    return video_link
                self._log(f"patrón '{nombre}' sin coincidencias", "info")
            except Exception as e:
                self._log(f"patrón '{nombre}' falló: {e}", "fail")

        self._log("ningún patrón encontró el video", "warn")
        return None

    def _extraer_src_javascript(self, contenido):
        patron = r'src:\s*["\']([^"\']+)["\']'
        resultado = re.search(patron, contenido)
        return resultado.group(1) if resultado else None

    def _extraer_eval_unpack(self, contenido):
        if 'eval(function' in contenido:
            patron = r'eval\(function.*?(https?://[^\\]*\.mp4)'
            resultado = re.search(patron, contenido, re.DOTALL)
            return resultado.group(1) if resultado else None
        return None

    def _extraer_mp4_directo(self, contenido):
        patron = r'https?://[^"\' ]+\.mp4[^"\' ]*'
        resultado = re.search(patron, contenido)
        return resultado.group(0) if resultado else None

    def extraer(self, url):
        url_procesada = self.procesar_url(url)
        contenido = self.obtener_contenido(url_procesada)
        video_link = self.extraer_video_src(contenido)

        if not video_link:
            self._log("no se encontró el origen del video embebido", "fail")
            raise Exception("No se encontró el origen del video embebido")

        self._log(f"extracción completada: {video_link}", "ok")
        return video_link


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    debug = '--debug' in sys.argv or '-d' in sys.argv

    if not args:
        print("Error: URL no proporcionada", file=sys.stderr)
        print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    try:
        extractor = MP4UploadExtractor(debug=debug)
        video_link = extractor.extraer(args[0])
        print(video_link)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
