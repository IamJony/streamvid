#!/usr/bin/env python3
# Extractor para filemoon, sfastwish by IamJony

import sys
import re
from urllib.parse import urlparse
from requests_html import HTMLSession
from real_headers import real_headers

from ..unpacker import unpack_eval_script


class FileMoonExtractor:
    """Clase para extraer videos de FileMoon"""

    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug
        self.headers = None

    # ---------- API pública ----------

    def soporta(self, url):
        return "filemoon" in url or "sfastwish" in url or "flaswish" in url

    def extraer(self, url):
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

            self._log(f"extracción completada: {video_link}", "ok")
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
        """Headers exactos que el CDN espera. Disponible tras extraer()."""
        return dict(self.headers) if self.headers else None

    # ---------- Logging ----------

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[filemoon] {icons.get(level, '·')} {msg}", file=sys.stderr)

    # ---------- HTTP ----------

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

    # ---------- Parsing ----------

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
        master_match = re.search(master_pattern, texto)
        if master_match:
            enlace = master_match.group(1)
            self._log(f"master.m3u8 encontrado: {enlace}", "ok")
            return enlace

        m3u8_pattern = r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)'
        m3u8_match = re.search(m3u8_pattern, texto)
        if m3u8_match:
            enlace = m3u8_match.group(1)
            self._log(f".m3u8 alternativo encontrado: {enlace}", "ok")
            return enlace

        self._log("no se encontró ningún .m3u8", "warn")
        return None


def _main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    debug = '--debug' in sys.argv or '-d' in sys.argv

    if not args:
        if debug:
            print("Error: URL no proporcionada", file=sys.stderr)
            print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    extractor = FileMoonExtractor(debug=debug)
    extractor.extraer_y_mostrar(args[0])


if __name__ == "__main__":
    _main()
