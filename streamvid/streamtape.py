#!/usr/bin/env python3
# Extractor para streamtape by IamJony

import sys
import re
from requests_html import HTMLSession
from real_headers import real_headers

# Headers y User-agent aletorios
random_headers = real_headers()


class StreamtapeExtractor:
    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[streamtape] {icons.get(level, '·')} {msg}", file=sys.stderr)

    def procesar_url(self, url):
        self._log(f"procesando URL: {url}", "step")

        patron = r'/e/([a-zA-Z0-9]+)'
        match = re.search(patron, url)
        if match:
            local_id = match.group(1)
            url = "https://strtape.cloud/e/" + local_id
            self._log(f"URL convertida: {url}", "ok")
            return url
        else:
            self._log("no se encontró un ID en la URL", "fail")
            return None

    def obtener_contenido(self, url):
        self._log(f"descargando: {url}", "step")
        try:
            headers = random_headers
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            self._log(f"HTML obtenido ({len(response.text)} bytes)", "ok")
            return response.text
        except Exception as e:
            self._log(f"error de descarga: {e}", "fail")
            raise Exception(f"Error al descargar la página: {e}")

    def extraer_video_src(self, contenido):
        if "document.getElementById('captchalink')" in contenido:
            self._log("detectado captchalink", "step")
            match = re.search(
                r"innerHTML = '([^']+)'\+\s*\('([^']+)'\)", contenido)
            if match:
                parte1 = match.group(1)
                parte2 = match.group(2)[4:]
                link = f"https:{parte1}{parte2}&stream=1"
                self._log(f"link extraído: {link}", "ok")
                return link
            self._log("captchalink presente pero sin match", "warn")

        if "document.getElementById('botlink')" in contenido:
            self._log("detectado botlink", "step")
            match = re.search(
                r"innerHTML = '([^']+)'\+\s*\('([^']+)'\)", contenido)
            if match:
                parte1 = match.group(1)
                parte2 = match.group(2)[4:]
                link = f"https:{parte1}{parte2}&stream=1"
                self._log(f"link extraído: {link}", "ok")
                return link
            self._log("botlink presente pero sin match", "warn")

        self._log("no se encontró captchalink ni botlink", "warn")
        return None

    def extraer(self, url):
        url_procesada = self.procesar_url(url)
        if not url_procesada:
            self._log("no se pudo procesar la URL", "fail")
            raise Exception("No se pudo procesar la URL")

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
        extractor = StreamtapeExtractor(debug=debug)
        video_link = extractor.extraer(args[0])
        print(video_link)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
