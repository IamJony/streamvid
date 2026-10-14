#!/usr/bin/env python3
# Extractor para streamtape by IamJony

import sys
import re
from urllib.parse import urlparse
from requests_html import HTMLSession
from real_headers import real_headers


class StreamtapeExtractor:
    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug
        self.headers = None

    # ---------- API pública ----------

    def soporta(self, url):
        return "streamtape" in url or "strtape" in url

    def extraer(self, url):
        url_procesada = self._procesar_url(url)
        if not url_procesada:
            self._log("no se pudo procesar la URL", "fail")
            raise Exception("No se pudo procesar la URL")

        contenido = self._obtener_contenido(url_procesada)
        video_link = self._extraer_video_src(contenido)

        if not video_link:
            self._log("no se encontró el origen del video embebido", "fail")
            raise Exception("No se encontró el origen del video embebido")

        self._log(f"extracción completada: {video_link}", "ok")
        return video_link

    def extraer_y_mostrar(self, url):
        try:
            video_link = self.extraer(url)
            print(video_link)
            return video_link
        except Exception as e:
            if self.debug:
                print(f"[streamtape] error: {e}", file=sys.stderr)
            sys.exit(1)

    def obtener_headers(self):
        return dict(self.headers) if self.headers else None

    # ---------- Logging ----------

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[streamtape] {icons.get(level, '·')} {msg}", file=sys.stderr)

    # ---------- URL ----------

    def _procesar_url(self, url):
        self._log(f"procesando URL: {url}", "step")

        patron = r'/e/([a-zA-Z0-9]+)'
        match = re.search(patron, url)
        if match:
            local_id = match.group(1)
            url = "https://strtape.cloud/e/" + local_id
            self._log(f"URL convertida: {url}", "ok")
            return url

        self._log("no se encontró un ID en la URL", "fail")
        return None

    # ---------- HTTP ----------

    def _obtener_contenido(self, url):
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

    def _extraer_video_src(self, contenido):
        for marker in ("captchalink", "botlink"):
            if f"document.getElementById('{marker}')" in contenido:
                self._log(f"detectado {marker}", "step")
                match = re.search(
                    r"innerHTML = '([^']+)'\+\s*\('([^']+)'\)", contenido
                )
                if match:
                    parte1 = match.group(1)
                    parte2 = match.group(2)[4:]
                    link = f"https:{parte1}{parte2}&stream=1"
                    self._log(f"link extraído: {link}", "ok")
                    return link
                self._log(f"{marker} presente pero sin match", "warn")

        self._log("no se encontró captchalink ni botlink", "warn")
        return None


def _main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    debug = '--debug' in sys.argv or '-d' in sys.argv

    if not args:
        if debug:
            print("Error: URL no proporcionada", file=sys.stderr)
            print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    extractor = StreamtapeExtractor(debug=debug)
    extractor.extraer_y_mostrar(args[0])


if __name__ == "__main__":
    _main()
