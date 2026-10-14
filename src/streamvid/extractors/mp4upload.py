#!/usr/bin/env python3
# Extractor para mp4upload by IamJony

import sys
import re
from urllib.parse import urlparse
from requests_html import HTMLSession
from real_headers import real_headers


class MP4UploadExtractor:
    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug
        self.headers = None

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[mp4upload] {icons.get(level, '·')} {msg}", file=sys.stderr)

    def soporta(self, url):
        return "mp4upload.com" in url

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

    def _es_pagina_login(self, response):
        if "/login" in response.url:
            return True
        html = response.text
        if 'action="/login"' in html or 'name="login"' in html:
            return True
        return False

    def obtener_contenido(self, url):
        self._log(f"descargando: {url}", "step")
        try:
            headers = real_headers()
            response = self.session.get(url, headers=headers, allow_redirects=True)
            response.raise_for_status()

            if self._es_pagina_login(response):
                self._log(f"redirigido a login ({response.url}) → video no existe", "fail")
                raise Exception("Video no encontrado (redirigido a /login)")

            self._log(f"HTML obtenido ({len(response.text)} bytes)", "ok")

            self.headers = dict(headers)
            self.headers["Referer"] = self._dominio_base(response.url)

            return response.text
        except Exception as e:
            self._log(f"error de descarga: {e}", "fail")
            raise

    @staticmethod
    def _dominio_base(url):
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}/"

    def obtener_headers(self):
        return dict(self.headers) if self.headers else None

    def _es_link_valido(self, link):
        if not link or not re.match(r'https?://', link):
            return False
        if re.search(r'\.(png|jpg|jpeg|gif|svg|ico|css|js|woff2?)(\?|$)', link, re.I):
            return False
        return bool(re.search(r'\.(mp4|m3u8)(\?|$)', link, re.I))

    def extraer_video_src(self, contenido):
        extractores = [
            self._extraer_src_javascript,
            self._extraer_eval_unpack,
            self._extraer_mp4_directo,
        ]

        for extractor in extractores:
            nombre = extractor.__name__
            self._log(f"probando patrón: {nombre}", "step")
            try:
                video_link = extractor(contenido)
                if video_link and self._es_link_valido(video_link):
                    self._log(f"patrón '{nombre}' encontró: {video_link}", "ok")
                    return video_link
                if video_link:
                    self._log(f"patrón '{nombre}' devolvió algo inválido: {video_link}", "warn")
            except Exception as e:
                self._log(f"patrón '{nombre}' falló: {e}", "fail")

        self._log("ningún patrón encontró el video", "warn")
        return None

    def _extraer_src_javascript(self, contenido):
        patron = r'src:\s*["\']([^"\']+\.(?:mp4|m3u8)[^"\']*)["\']'
        resultado = re.search(patron, contenido)
        return resultado.group(1) if resultado else None

    def _extraer_eval_unpack(self, contenido):
        if 'eval(function' in contenido:
            patron = r'eval\(function.*?(https?://[^\\]*\.mp4)'
            resultado = re.search(patron, contenido, re.DOTALL)
            return resultado.group(1) if resultado else None
        return None

    def _extraer_mp4_directo(self, contenido):
        patron = r'(https?://[^"\'\s<>]+\.mp4)(?:[?"\'\s<>]|$)'
        resultado = re.search(patron, contenido)
        return resultado.group(1) if resultado else None

    def extraer(self, url):
        url_procesada = self.procesar_url(url)
        contenido = self.obtener_contenido(url_procesada)
        video_link = self.extraer_video_src(contenido)

        if not video_link:
            self._log("no se encontró el origen del video embebido", "fail")
            raise Exception("No se encontró el origen del video embebido")

        self._log(f"extracción completada: {video_link}", "ok")
        return video_link


def _main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    debug = '--debug' in sys.argv or '-d' in sys.argv

    if not args:
        if debug:
            print("Error: URL no proporcionada", file=sys.stderr)
            print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    try:
        extractor = MP4UploadExtractor(debug=debug)
        video_link = extractor.extraer(args[0])
        print(video_link)
    except Exception as e:
        if debug:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()
