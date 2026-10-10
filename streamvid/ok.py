#!/usr/bin/env python3
# Extractor para OK.ru (videoembed) by IamJony style

import sys
import re
import html
import json
from requests_html import HTMLSession
from real_headers import real_headers

# Headers y User-agent aleatorios
random_headers = real_headers()


class OkRuExtractor:
    """Clase para extraer el HLS de OK.ru / Odnoklassniki (videoembed)."""

    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug

        # Bloque principal: <div data-module="OKVideo" ... data-options="{...}">
        self.options_pattern = re.compile(
            r'data-module=["\']OKVideo["\'][^>]*?data-options="([^"]*)"',
            re.DOTALL,
        )
        # Fallback 1: cualquier data-options con movieId
        self.any_options_pattern = re.compile(
            r'data-options="([^"]*)"', re.DOTALL
        )
        # Fallback 2: bloque "movie" crudo
        self.movie_pattern = re.compile(
            r'"movie"\s*:\s*(\{.*?\})\s*,\s*"failoverHosts"', re.DOTALL
        )
        # Fallback 3: URL HLS directa en el HTML
        self.hls_pattern = re.compile(
            r'https?://[^\s"\'&<>]+?/ondemand/hls[0-9_]+[^\s"\'&<>]*?\.m3u8',
            re.IGNORECASE,
        )

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[okru] {icons.get(level, '·')} {msg}", file=sys.stderr)

    def _build_headers(self):
        """Headers tipo navegador para que OK.ru devuelva el HTML completo."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://ok.ru/",
            "Upgrade-Insecure-Requests": "1",
        }
        if isinstance(random_headers, dict):
            headers.update({k: v for k, v in random_headers.items() if k not in headers})
        return headers

    def obtener_html(self, url):
        self._log(f"descargando: {url}", "step")
        try:
            response = self.session.get(
                url, headers=self._build_headers(), allow_redirects=True
            )
            response.raise_for_status()
            self._log(
                f"HTML obtenido ({len(response.text)} bytes) status={response.status_code}",
                "ok",
            )
            if "ondemandHls" not in response.text:
                self._log("el HTML NO contiene 'ondemandHls'", "warn")
            return response.text
        except Exception as e:
            self._log(f"error de descarga: {e}", "fail")
            raise Exception(f"Error al descargar la página: {e}")

    def _parse_json(self, raw):
        """data-options viene con &quot; escapados; los des-escapa y parsea."""
        try:
            return json.loads(html.unescape(raw))
        except json.JSONDecodeError as err:
            self._log(f"JSON inválido: {err}", "fail")
            return None

    def extraer_options(self, html_text):
        """Devuelve el dict data-options del reproductor OKVideo (con fallbacks)."""
        self._log("buscando bloque data-module=OKVideo", "step")

        match = self.options_pattern.search(html_text)
        if match:
            self._log("bloque OKVideo encontrado", "ok")
            data = self._parse_json(match.group(1))
            if data:
                return data
            self._log("JSON del bloque OKVideo inválido, probando fallbacks", "warn")

        self._log("probando data-options genérico", "warn")
        for raw in self.any_options_pattern.findall(html_text):
            data = self._parse_json(raw)
            if data and "movieId" in data:
                return data

        self._log("probando bloque movie crudo", "warn")
        match = self.movie_pattern.search(html_text)
        if match:
            data = self._parse_json(match.group(1))
            if data:
                return {"flashvars": {"metadata": {"movie": data}}}

        return None

    def extraer_hls_de_options(self, options):
        """Saca flashvars.ondemandHls del dict de data-options."""
        if not options:
            return None
        flashvars = options.get("flashvars") or {}
        hls = flashvars.get("ondemandHls")
        if hls:
            self._log(f"HLS en flashvars: {hls}", "ok")
        else:
            self._log("no se encontró ondemandHls en flashvars", "warn")
        return hls

    def buscar_hls_regex(self, html_text):
        """Fallback: busca la URL HLS directamente con regex estricto."""
        self._log("fallback: buscando URL HLS con regex", "warn")
        match = self.hls_pattern.search(html_text)
        if not match:
            self._log("no se encontró HLS por regex", "warn")
            return None
        hls = match.group(0)
        hls = hls.replace("&quot;", "").replace("\\u0026", "&").replace("&amp;", "&")
        self._log(f"HLS encontrado por regex: {hls}", "ok")
        return hls

    def extraer(self, url):
        """Flujo completo: descarga -> options -> HLS -> fallback regex."""
        try:
            html_text = self.obtener_html(url)

            options = self.extraer_options(html_text)
            hls = self.extraer_hls_de_options(options)
            if hls:
                self._log(f"extracción completada: {hls}", "ok")
                return hls

            hls = self.buscar_hls_regex(html_text)
            if hls:
                self._log(f"extracción completada (regex): {hls}", "ok")
                return hls

            raise Exception("No se pudo encontrar el enlace HLS")

        except Exception as e:
            self._log(f"error fatal: {e}", "fail")
            raise

    def extraer_y_mostrar(self, url):
        try:
            video_link = self.extraer(url)
            print(video_link)
            return video_link
        except Exception as e:
            self._log(f"error fatal: {e}", "fail")
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    debug = '--debug' in sys.argv or '-d' in sys.argv

    if not args:
        print("Error: URL no proporcionada", file=sys.stderr)
        print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    url = args[0]

    extractor = OkRuExtractor(debug=debug)
    extractor.extraer_y_mostrar(url)


if __name__ == "__main__":
    main()
