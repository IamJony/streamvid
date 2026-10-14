#!/usr/bin/env python3
# Extractor para OK.ru (videoembed) by IamJony

import sys
import re
import html
import json
from urllib.parse import urlparse
from requests_html import HTMLSession
from real_headers import real_headers


class OkRuExtractor:
    """Extrae el HLS de OK.ru / Odnoklassniki (videoembed)."""

    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug
        self.headers = None

        self.options_pattern = re.compile(
            r'data-module=["\']OKVideo["\'][^>]*?data-options="([^"]*)"',
            re.DOTALL,
        )
        self.any_options_pattern = re.compile(
            r'data-options="([^"]*)"', re.DOTALL
        )
        self.movie_pattern = re.compile(
            r'"movie"\s*:\s*(\{.*?\})\s*,\s*"failoverHosts"', re.DOTALL
        )
        self.hls_pattern = re.compile(
            r'https?://[^\s"\'&<>]+?/ondemand/hls[0-9_]+[^\s"\'&<>]*?\.m3u8',
            re.IGNORECASE,
        )

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[okru] {icons.get(level, '·')} {msg}", file=sys.stderr)

    # ---------- API pública ----------

    def soporta(self, url):
        return "ok.ru" in url or "odnoklassniki.ru" in url

    def extraer(self, url):
        try:
            html_text = self._obtener_html(url)

            options = self._extraer_options(html_text)
            hls = self._extraer_hls_de_options(options)
            if hls:
                self._log(f"extracción completada: {hls}", "ok")
                return hls

            hls = self._buscar_hls_regex(html_text)
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
            if self.debug:
                print(f"[okru] error: {e}", file=sys.stderr)
            sys.exit(1)

    def obtener_headers(self):
        return dict(self.headers) if self.headers else None

    # ---------- HTTP ----------

    def _build_headers(self):
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
        extra = real_headers()
        if isinstance(extra, dict):
            headers.update({k: v for k, v in extra.items() if k not in headers})
        return headers

    def _obtener_html(self, url):
        self._log(f"descargando: {url}", "step")
        try:
            headers = self._build_headers()
            response = self.session.get(
                url, headers=headers, allow_redirects=True
            )
            response.raise_for_status()
            self._log(
                f"HTML obtenido ({len(response.text)} bytes) status={response.status_code}",
                "ok",
            )
            if "ondemandHls" not in response.text:
                self._log("el HTML NO contiene 'ondemandHls'", "warn")

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

    def _parse_json(self, raw):
        try:
            return json.loads(html.unescape(raw))
        except json.JSONDecodeError as err:
            self._log(f"JSON inválido: {err}", "fail")
            return None

    def _extraer_options(self, html_text):
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

    def _extraer_hls_de_options(self, options):
        if not options:
            return None
        flashvars = options.get("flashvars") or {}
        hls = flashvars.get("ondemandHls")
        if hls:
            self._log(f"HLS en flashvars: {hls}", "ok")
        else:
            self._log("no se encontró ondemandHls en flashvars", "warn")
        return hls

    def _buscar_hls_regex(self, html_text):
        self._log("fallback: buscando URL HLS con regex", "warn")
        match = self.hls_pattern.search(html_text)
        if not match:
            self._log("no se encontró HLS por regex", "warn")
            return None
        hls = match.group(0)
        hls = hls.replace("&quot;", "").replace("\\u0026", "&").replace("&amp;", "&")
        self._log(f"HLS encontrado por regex: {hls}", "ok")
        return hls


def _main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    debug = '--debug' in sys.argv or '-d' in sys.argv

    if not args:
        if debug:
            print("Error: URL no proporcionada", file=sys.stderr)
            print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    extractor = OkRuExtractor(debug=debug)
    extractor.extraer_y_mostrar(args[0])


if __name__ == "__main__":
    _main()
