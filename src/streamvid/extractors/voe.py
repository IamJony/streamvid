#!/usr/bin/env python3
"""
Extractor para VOE (voe.sx / sfastwish.com).
IamJony

Internamente hace dos pasos (descargar HTML + parsear JSON ofuscado),
pero eso queda encapsulado en `extraer()`.
"""
import sys
import re
import base64
import binascii
import json
from urllib.parse import urlparse

from requests_html import HTMLSession

from real_headers import real_headers


class VoeExtractor:
    """Extractor para VOE. Encapsula descarga + decodificación."""

    DOMINIOS = ("voe.sx", "sfastwish.com")

    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug
        self.headers = None
        self.redirect_pattern = re.compile(r"https?://[^'\"<>]+")
        self.json_pattern = re.compile(
            r'<script\s+type=["\']application/json["\']>(.*?)</script>', re.DOTALL
        )
        self.junk_parts = ["@$", "^^", "~@", "%?", "*~", "!!", "#&"]

    # ---------- API pública ----------

    def soporta(self, url: str) -> bool:
        return any(dominio in url for dominio in self.DOMINIOS)

    def extraer(self, url: str):
        contenido = self._obtener_contenido(url)
        return self._extraer_video_src(contenido)

    def obtener_headers(self):
        """Headers exactos que el CDN espera. Disponible tras extraer()."""
        return dict(self.headers) if self.headers else None

    # ---------- Logging ----------

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[voe] {icons.get(level, '·')} {msg}", file=sys.stderr)

    # ---------- Decodificación (interna) ----------

    def _shift_letters(self, input_str):
        result = []
        for c in input_str:
            code = ord(c)
            if 65 <= code <= 90:
                code = (code - 65 + 13) % 26 + 65
            elif 97 <= code <= 122:
                code = (code - 97 + 13) % 26 + 97
            result.append(chr(code))
        return "".join(result)

    def _replace_junk(self, input_str):
        for part in self.junk_parts:
            input_str = input_str.replace(part, "_")
        return input_str

    def _shift_back(self, s, n):
        return "".join(chr(ord(c) - n) for c in s)

    def _decode_voe_string(self, encoded):
        self._log(f"decodificando string ({len(encoded)} chars)", "step")
        try:
            step1 = self._shift_letters(encoded)
            step2 = self._replace_junk(step1).replace("_", "")
            step3 = base64.b64decode(step2).decode()
            step4 = self._shift_back(step3, 3)
            step5 = base64.b64decode(step4[::-1]).decode()
            result = json.loads(step5)
            self._log("JSON parseado", "ok")
            return result
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as err:
            raise ValueError(f"Error decodificando VOE: {err}")

    def _extract_voe_source_from_html(self, html):
        self._log("buscando bloques <script type=application/json>", "step")
        try:
            script_blocks = self.json_pattern.findall(html)
            if not script_blocks:
                return None

            for i, script_block in enumerate(script_blocks, 1):
                encoded_text = script_block.strip()
                if encoded_text.startswith('"') and encoded_text.endswith('"'):
                    encoded_text = encoded_text[1:-1]

                try:
                    encoded_text = encoded_text.encode().decode("unicode_escape")
                except UnicodeDecodeError:
                    pass

                try:
                    decoded = self._decode_voe_string(encoded_text)
                    source = decoded.get("source")
                    if source:
                        return source
                except ValueError:
                    continue

            return None
        except Exception as e:
            self._log(f"error en extracción: {e}", "fail")
            return None

    # ---------- Descarga (interna) ----------

    def _obtener_contenido(self, url):
        self._log(f"descargando: {url}", "step")
        try:
            headers = real_headers()
            response = self.session.get(url, headers=headers, allow_redirects=True)
            self._log(f"HTML inicial ({len(response.text)} bytes)", "ok")

            redirect_match = self.redirect_pattern.search(response.text)
            if redirect_match:
                redirect_url = redirect_match.group(0)
                self._log(f"redirección detectada: {redirect_url}", "step")
                response = self.session.get(
                    redirect_url, headers=headers, allow_redirects=True
                )
                self._log(f"HTML redirigido ({len(response.text)} bytes)", "ok")

            # Guardar headers usados + Referer del dominio final
            self.headers = dict(headers)
            self.headers["Referer"] = self._dominio_base(response.url)

            return response.text

        except Exception as e:
            self._log(f"error de descarga: {e}", "fail")
            raise Exception(f"Error al descargar la página: {e}")

    @staticmethod
    def _dominio_base(url):
        """https://sfastwish.com/e/abc → https://sfastwish.com/"""
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}/"

    # ---------- Parseo (interna) ----------

    def _extraer_video_src(self, contenido):
        self._log("extrayendo source del HTML", "step")
        try:
            source = self._extract_voe_source_from_html(contenido)
            if source:
                return source
        except Exception as e:
            self._log(f"error: {e}", "fail")

        self._log("no se encontró source", "warn")
        return None


# ---------- CLI para depurar voe solo ----------

def _main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    debug = "--debug" in sys.argv or "-d" in sys.argv

    if not args:
        print(f"Uso: {sys.argv[0]} [--debug] <URL_VOE>", file=sys.stderr)
        sys.exit(1)

    url = args[0]
    extractor = VoeExtractor(debug=debug)

    try:
        video = extractor.extraer(url)
        if video:
            print(video)
            if debug:
                print("\n# Headers:", file=sys.stderr)
                for k, v in (extractor.obtener_headers() or {}).items():
                    print(f"#   {k}: {v}", file=sys.stderr)
        else:
            sys.exit(1)
    except Exception as e:
        extractor._log(f"error fatal: {e}", "fail")
        sys.exit(1)


if __name__ == "__main__":
    _main()
