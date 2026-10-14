#!/usr/bin/env python3
# Extractor universal by IamJony

import sys
import re
import os
import json
import base64
import binascii
import subprocess
from urllib.parse import urlparse
from requests_html import HTMLSession
from real_headers import real_headers


class UniversalExtractor:
    """
    Extractor universal que NO depende del dominio.
    Aplica todas las estrategias conocidas en orden y devuelve
    el primer enlace válido que encuentre.
    """

    def __init__(self, session=None, temp_file='/tmp/eval.js', debug=False):
        self.session = session or HTMLSession()
        self.temp_file = temp_file
        self.debug = debug
        self.headers = None

        self.redirect_pattern = re.compile(r"https?://[^'\"<>]+")
        self.json_pattern = re.compile(
            r'<script\s+type=["\']application/json["\']>(.*?)</script>',
            re.DOTALL,
        )
        self.junk_parts = ["@$", "^^", "~@", "%?", "*~", "!!", "#&"]

    # ============================================================
    #                     API PÚBLICA
    # ============================================================
    def soporta(self, url):
        """Universal acepta cualquier URL: es el fallback."""
        return True

    def extraer(self, url, _recursion=0):
        if _recursion > 3:
            raise Exception("Demasiadas redirecciones internas")

        self._log(f"Descargando: {url}")
        try:
            html = self._obtener_html(url, allow_redirects=True)
        except Exception as e:
            raise Exception(f"No se pudo obtener la página: {e}")

        estrategias = [
            ("patrones-directos", self._estrategia_patrones_directos),
            ("eval-unpack",        self._estrategia_eval_unpack),
            ("voe",                self._estrategia_voe),
            ("streamtape",         self._estrategia_streamtape),
        ]

        for nombre, fn in estrategias:
            try:
                self._log(f"Probando estrategia: {nombre}")
                resultado = fn(url, html)
                if resultado:
                    self._log(f"✔ Éxito con '{nombre}': {resultado}")
                    return resultado
            except Exception as e:
                self._log(f"✘ Estrategia '{nombre}' falló: {e}")
                continue

        try:
            self._log("Probando estrategia: redirección")
            next_url = self._estrategia_redireccion(url, html)
            if next_url:
                return self.extraer(next_url, _recursion + 1)
        except Exception as e:
            self._log(f"✘ Redirección falló: {e}")

        raise Exception("Ninguna estrategia pudo extraer el video")

    def extraer_y_mostrar(self, url):
        try:
            link = self.extraer(url)
            print(link)
            return link
        except Exception as e:
            if self.debug:
                print(f"[universal] error: {e}", file=sys.stderr)
            sys.exit(1)

    def obtener_headers(self):
        return dict(self.headers) if self.headers else None

    # ============================================================
    #                     LOG
    # ============================================================
    def _log(self, msg):
        if self.debug:
            print(f"[universal] {msg}", file=sys.stderr)

    # ============================================================
    #                     UTILIDADES HTTP
    # ============================================================
    def _obtener_html(self, url, allow_redirects=True):
        try:
            headers = real_headers()
            response = self.session.get(
                url, headers=headers, allow_redirects=allow_redirects
            )
            response.raise_for_status()

            self.headers = dict(headers)
            self.headers["Referer"] = self._dominio_base(response.url)

            return response.text
        except Exception as e:
            raise Exception(f"Error al descargar la página: {e}")

    @staticmethod
    def _dominio_base(url):
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}/"

    def _limpiar_temp(self):
        try:
            if os.path.exists(self.temp_file):
                os.remove(self.temp_file)
        except Exception:
            pass

    # ============================================================
    #        ESTRATEGIA 1: eval-unpacker
    # ============================================================
    def _buscar_script_eval(self, html):
        patron = (
            r'<script[^>]*type=[\'"]text/javascript[\'"][^>]*>'
            r'.*?eval\(function\(p,a,c,k,e,d\).*?</script>'
        )
        m = re.search(patron, html, re.DOTALL | re.IGNORECASE)
        return m.group() if m else None

    def _ejecutar_eval_unpack(self):
        try:
            resultado = subprocess.run(
                ['eval-unpacker', self.temp_file],
                capture_output=True, text=True, check=True
            )
            return resultado.stdout
        except subprocess.CalledProcessError as e:
            raise Exception(f"Error al ejecutar eval-unpack: {e.stderr}")
        except FileNotFoundError:
            raise Exception("No se encuentra 'eval-unpacker'. ¿Está instalado?")

    @staticmethod
    def _extraer_m3u8(texto):
        m = re.search(r'(https?://[^"\'\s]+master\.m3u8[^"\'\s]*)', texto)
        if m:
            return m.group(1)
        m = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', texto)
        return m.group(1) if m else None

    def _estrategia_eval_unpack(self, url, html):
        script = self._buscar_script_eval(html)
        if not script:
            return None

        self._log("Estrategia eval-unpack: script encontrado")
        try:
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                f.write(script)
            unpacked = self._ejecutar_eval_unpack()
            return self._extraer_m3u8(unpacked) or self._extraer_mp4(unpacked)
        finally:
            self._limpiar_temp()

    # ============================================================
    #                  ESTRATEGIA 2: VOE
    # ============================================================
    @staticmethod
    def _voe_shift_letters(s):
        out = []
        for c in s:
            code = ord(c)
            if 65 <= code <= 90:
                code = (code - 65 + 13) % 26 + 65
            elif 97 <= code <= 122:
                code = (code - 97 + 13) % 26 + 97
            out.append(chr(code))
        return "".join(out)

    def _voe_replace_junk(self, s):
        for part in self.junk_parts:
            s = s.replace(part, "_")
        return s

    @staticmethod
    def _voe_shift_back(s, n):
        return "".join(chr(ord(c) - n) for c in s)

    def _voe_decode_string(self, encoded):
        try:
            step1 = self._voe_shift_letters(encoded)
            step2 = self._voe_replace_junk(step1).replace("_", "")
            step3 = base64.b64decode(step2).decode()
            step4 = self._voe_shift_back(step3, 3)
            step5 = base64.b64decode(step4[::-1]).decode()
            return json.loads(step5)
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as err:
            raise ValueError(f"Error decodificando VOE: {err}")

    def _voe_extraer_source(self, html):
        for block in self.json_pattern.findall(html):
            encoded = block.strip()
            if encoded.startswith('"') and encoded.endswith('"'):
                encoded = encoded[1:-1]
            try:
                encoded = encoded.encode().decode("unicode_escape")
            except UnicodeDecodeError:
                pass
            try:
                decoded = self._voe_decode_string(encoded)
                source = decoded.get("source")
                if source:
                    return source
            except ValueError:
                continue
        return None

    def _estrategia_voe(self, url, html):
        src = self._voe_extraer_source(html)
        if src:
            self._log("Estrategia VOE: source encontrado")
            return src
        return None

    # ============================================================
    #          ESTRATEGIA 3: Patrones directos
    # ============================================================
    def _estrategia_patrones_directos(self, url, html):
        m = re.search(r'(https?://[^"\'\s<>]+master\.m3u8[^"\'\s<>]*)', html)
        if m:
            self._log("Estrategia directa: master.m3u8")
            return m.group(1)

        m = re.search(r'(https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*)', html)
        if m:
            self._log("Estrategia directa: .m3u8")
            return m.group(1)

        m = re.search(
            r'src\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html
        )
        if m:
            self._log("Estrategia directa: src: en JS")
            return m.group(1)

        m = re.search(r'(https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*)', html)
        if m:
            self._log("Estrategia directa: .mp4")
            return m.group(1)

        return None

    # ============================================================
    #        ESTRATEGIA 4: Streamtape
    # ============================================================
    def _estrategia_streamtape(self, url, html):
        if ("document.getElementById('captchalink')" in html or
                "document.getElementById('botlink')" in html):
            m = re.search(
                r"innerHTML = '([^']+)'\+\s*\('([^']+)'\)", html
            )
            if m:
                parte1 = m.group(1)
                parte2 = m.group(2)[4:]
                self._log("Estrategia streamtape: link encontrado")
                return f"https:{parte1}{parte2}&stream=1"
        return None

    # ============================================================
    #     ESTRATEGIA 5: Redirección interna
    # ============================================================
    def _estrategia_redireccion(self, url, html):
        m = re.search(
            r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE
        )
        if not m:
            m = re.search(
                r'(?:window\.location|location\.href)\s*=\s*["\']([^"\']+)["\']',
                html,
            )
        if m:
            next_url = m.group(1)
            if next_url.startswith('//'):
                next_url = 'https:' + next_url
            elif next_url.startswith('/'):
                from urllib.parse import urljoin
                next_url = urljoin(url, next_url)
            if next_url.startswith('http'):
                self._log(f"Estrategia redirección: siguiendo {next_url}")
                return next_url
        return None

    # ============================================================
    #                 Helpers
    # ============================================================
    @staticmethod
    def _extraer_mp4(texto):
        m = re.search(r'(https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*)', texto)
        return m.group(1) if m else None


def _main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    debug = '--debug' in sys.argv or '-d' in sys.argv

    if not args:
        if debug:
            print("Error: URL no proporcionada", file=sys.stderr)
            print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    url = args[0]
    extractor = UniversalExtractor(debug=debug)
    extractor.extraer_y_mostrar(url)


if __name__ == "__main__":
    _main()
