#!/usr/bin/env python3
"""
Extractor para Wikipedia (wikipedia.

Técnica de extracción:
  - <describe brevemente cómo se obtiene el link>
  - Wikipedia no sirve video, así que el ejemplo devuelve el primer
    enlace .mp4/.m3u8 que aparezca en el HTML, solo como demostración.

Internamente hace dos pasos (descargar HTML + parsear), pero eso queda
encapsulado en `extraer()`.
"""

import sys
import re
from urllib.parse import urlparse

from requests_html import HTMLSession

from real_headers import real_headers


class WikipediaExtractor:
    """Extractor para Wikipedia. Encapsula descarga + parseo."""

    # Dominios que este extractor reconoce. Se usan en soporta().
    DOMINIOS = ("wikipedia.org", "wikipedia")

    # ------------------------------------------------------------------ #
    # Constructor
    # ------------------------------------------------------------------ #
    def __init__(self, session=None, debug=False):
        """
        __init__ recibe por defecto:
          - session: inyectable para tests
          - debug:   controla el logging
          - headers: empieza como None y se rellena tras la primera petición
        """
        self.session = session or HTMLSession()
        self.debug = debug
        self.headers = None  # ← se rellena en la primera petición

        # Patrones precompilados
        self.link_pattern = re.compile(
            r'https?://[^\s"\'<>]+\.(?:mp4|m3u8)(?:\?[^\s"\'<>]*)?',
            re.IGNORECASE,
        )

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def soporta(self, url: str) -> bool:
        """True si el extractor puede manejar esa URL. Sin peticiones HTTP."""
        return any(dominio in url for dominio in self.DOMINIOS)

    def extraer(self, url: str):
        """
        Único punto de entrada. Devuelve el link del video (str) o lanza
        excepción si falla. No imprime nada.
        """
        contenido = self._obtener_contenido(url)
        video = self._extraer_video_src(contenido)
        if not video:
            raise Exception("No se encontró el origen del video")
        return video

    def obtener_headers(self):
        """Headers que el CDN espera. Disponible tras llamar a extraer()."""
        return dict(self.headers) if self.headers else None

    def extraer_y_mostrar(self, url: str):
        """Uso standalone: imprime el link o sale con código 1."""
        try:
            video_link = self.extraer(url)
            print(video_link)
            return video_link
        except Exception as e:
            if self.debug:
                print(f"[wikipedia] error: {e}", file=sys.stderr)
            sys.exit(1)

    # ------------------------------------------------------------------ #
    # Logging (todo a stderr, silenciado sin --debug)
    # ------------------------------------------------------------------ #
    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[wikipedia] {icons.get(level, '·')} {msg}", file=sys.stderr)

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #
    def _obtener_contenido(self, url):
        self._log(f"descargando: {url}", "step")
        try:
            headers = real_headers()  # ← por petición, no al importar
            response = self.session.get(
                url, headers=headers, allow_redirects=True
            )
            response.raise_for_status()

            # Detección de páginas de error que devuelven 200 OK
            if self._es_pagina_login(response):
                self._log(
                    f"redirigido a login ({response.url}) → video no existe",
                    "fail",
                )
                raise Exception("Video no encontrado (redirigido a /login)")

            self._log(f"HTML obtenido ({len(response.text)} bytes)", "ok")

            # Guardar headers usados + Referer del dominio final tras redirects
            self.headers = dict(headers)
            self.headers["Referer"] = self._dominio_base(response.url)

            return response.text
        except Exception as e:
            self._log(f"error de descarga: {e}", "fail")
            raise

    @staticmethod
    def _dominio_base(url):
        """https://es.wikipedia.org/wiki/X → https://es.wikipedia.org/"""
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}/"

    # ------------------------------------------------------------------ #
    # Detección de páginas de error
    # ------------------------------------------------------------------ #
    def _es_pagina_login(self, response):
        """
        Wikipedia no tiene login para videos, pero dejamos el hook por
        si el sitio real redirige a /login cuando el video no existe.
        """
        if "/login" in response.url:
            return True
        if 'action="/login"' in response.text:
            return True
        return False

    # ------------------------------------------------------------------ #
    # Parseo
    # ------------------------------------------------------------------ #
    def _extraer_video_src(self, contenido):
        """
        ==== SUSTITUIR POR LA LÓGICA REAL DEL SITIO ====
        Ejemplos según el sitio:
          - eval(function(p,a,c,k,e,d)) → eval-unpacker
          - JSON ofuscado (ROT13 + base64 anidado)
          - document.getElementById('captchalink') + concatenación
          - src: "..." en JS
          - data-module="OKVideo" con data-options (JSON escapado)

        Aquí (Wikipedia) solo buscamos el primer .mp4/.m3u8 como demo.
        """
        self._log("extrayendo source del HTML", "step")
        try:
            match = self.link_pattern.search(contenido)
            if match:
                source = match.group(0)
                if self._es_link_valido(source):
                    self._log(f"source encontrado: {source}", "ok")
                    return source
        except Exception as e:
            self._log(f"error en extracción: {e}", "fail")

        self._log("no se encontró source", "warn")
        return None

    # ------------------------------------------------------------------ #
    # Validación del link
    # ------------------------------------------------------------------ #
    def _es_link_valido(self, link):
        if not link or not re.match(r"https?://", link):
            return False
        if re.search(
            r"\.(png|jpg|jpeg|gif|svg|ico|css|js|woff2?)(\?|$)",
            link,
            re.I,
        ):
            return False
        return bool(re.search(r"\.(mp4|m3u8)(\?|$)", link, re.I))


# ---------------------------------------------------------------------- #
# CLI para depurar el extractor solo
# ---------------------------------------------------------------------- #
def _main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    debug = "--debug" in sys.argv or "-d" in sys.argv

    if not args:
        if debug:
            print("Error: URL no proporcionada", file=sys.stderr)
            print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    url = args[0]
    extractor = WikipediaExtractor(debug=debug)

    try:
        video = extractor.extraer(url)
        print(video)
        if debug:
            print("\n# Headers:", file=sys.stderr)
            for k, v in (extractor.obtener_headers() or {}).items():
                print(f"#   {k}: {v}", file=sys.stderr)
    except Exception as e:
        extractor._log(f"error fatal: {e}", "fail")
        sys.exit(1)


if __name__ == "__main__":
    _main()
