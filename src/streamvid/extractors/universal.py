#!/usr/bin/env python3
# Extractor universal by IamJony
# Versión portable para Kodi: sin curl_cffi, solo requests.

import sys
import re
import json
import base64
import binascii
import random
import string
import time
from urllib.parse import urlparse, urljoin

from requests_html import HTMLSession

from real_headers import real_headers
from ..unpacker import unpack_eval_script


class UniversalExtractor:
    """
    Extractor universal que NO depende del dominio.
    Aplica todas las estrategias conocidas en orden y devuelve
    el primer enlace válido que encuentre.
    """

    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug
        self.headers = None
        self.final_url = None

        self.redirect_pattern = re.compile(r"https?://[^'\"<>]+")
        self.json_pattern = re.compile(
            r'<script\s+type=["\']application/json["\']>(.*?)</script>',
            re.DOTALL,
        )
        self.junk_parts = ["@$", "^^", "~@", "%?", "*~", "!!", "#&"]

        # ---- Patrones DoodStream ----
        # Formato real: $.get('/pass_md5/HASH/TOKEN', ...)
        self.dood_pass_pattern = re.compile(
            r"(?:\$|jQuery)\s*\.\s*get\s*\(\s*['\"]"
            r"/pass_md5/([^'\"]+)['\"]",
            re.DOTALL,
        )
        self.dood_token_pattern = re.compile(
            r"token=([A-Za-z0-9]+)",
            re.DOTALL,
        )
        self.dood_url_pattern = re.compile(
            r"/(?:e|d)/[A-Za-z0-9]+", re.IGNORECASE
        )

    # ============================================================
    #                     API PÚBLICA
    # ============================================================
    def soporta(self, url):
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
            ("patrones-directos",  self._estrategia_patrones_directos),
            ("eval-unpack",        self._estrategia_eval_unpack),
            ("voe",                self._estrategia_voe),
            ("streamtape",         self._estrategia_streamtape),
            ("doodstream",         self._estrategia_doodstream),
        ]

        for nombre, fn in estrategias:
            try:
                self._log(f"Probando estrategia: {nombre}")
                resultado = fn(url, html)
                if resultado:
                    self._log(f"OK con '{nombre}': {resultado}")
                    return resultado
            except Exception as e:
                self._log(f"FALLO estrategia '{nombre}': {e}")
                continue

        try:
            self._log("Probando estrategia: redirección")
            next_url = self._estrategia_redireccion(url, html)
            if next_url:
                return self.extraer(next_url, _recursion + 1)
        except Exception as e:
            self._log(f"FALLO redirección: {e}")

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
            headers = self._headers_seguros()
            response = self.session.get(
                url,
                headers=headers,
                allow_redirects=allow_redirects,
                timeout=30,
            )
            response.raise_for_status()

            self.headers = dict(headers)
            self.final_url = str(response.url)
            self.headers["Referer"] = self._dominio_base(self.final_url)

            if self.debug:
                self._log(f"HTML final URL: {self.final_url}")
                self._log(
                    f"Contiene /pass_md5/: {'/pass_md5/' in response.text}"
                )

            return response.text
        except Exception as e:
            raise Exception(f"Error al descargar la página: {e}")

    def _headers_seguros(self):
        """real_headers() pero sin codificaciones que requests no maneja."""
        try:
            headers = dict(real_headers())
        except Exception:
            headers = {}
        # requests soporta gzip/deflate nativo. br/zstd requieren extras.
        headers["Accept-Encoding"] = "gzip, deflate"
        headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36",
        )
        return headers

    @staticmethod
    def _dominio_base(url):
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}/"

    # ============================================================
    #        ESTRATEGIA 5: DoodStream (pass_md5)
    # ============================================================
    def _es_doodstream(self, url, html):
        if self.dood_url_pattern.search(url):
            return True
        if "/pass_md5/" in html:
            return True
        if "makePlay" in html and "pass_md5" in html:
            return True
        return False

    def _estrategia_doodstream(self, url, html):
        if not self._es_doodstream(url, html):
            self._log("DoodStream: no aplica")
            return None

        self._log("DoodStream: extrayendo hash y token")

        m = self.dood_pass_pattern.search(html)
        if not m:
            self._log("DoodStream: no se encontró /pass_md5/")
            return None
        pass_path = m.group(1)

        if "/" in pass_path:
            pass_hash, token = pass_path.rsplit("/", 1)
        else:
            pass_hash = pass_path
            tm = self.dood_token_pattern.search(html)
            if not tm:
                self._log("DoodStream: no se encontró token")
                return None
            token = tm.group(1)

        self._log(f"DoodStream: hash={pass_hash} token={token}")

        # Sembrar cookies del HTML
        seed = {}
        for name in ("file_id", "aff", "ref_url", "dref_url"):
            cm = re.search(rf"\$\.cookie\('{name}',\s*'([^']*)'", html)
            if cm and cm.group(1):
                seed[name] = cm.group(1)

        # CLAVE: usar el dominio FINAL tras redirecciones
        final_url = self.final_url if self.final_url else url
        final_parsed = urlparse(final_url)
        base = f"{final_parsed.scheme}://{final_parsed.netloc}/"
        referer = final_url

        self._log(f"DoodStream: base final={base}")
        self._log(f"DoodStream: referer={referer}")

        pass_url = f"{base}pass_md5/{pass_hash}/{token}"

        data = None
        for attempt in range(3):
            self._log(f"DoodStream: GET {pass_url} (intento {attempt + 1})")
            data = self._dood_pass_request(pass_url, referer, seed)
            if data and data != "RELOAD" and not data.startswith("<"):
                break
            time.sleep(0.8 * (attempt + 1))

        if not data or data == "RELOAD" or data.startswith("<"):
            self._log("DoodStream: no se pudo obtener el video base")
            return None

        rand10 = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        expiry = int(time.time() * 1000)
        final_stream = f"{data}{rand10}?token={token}&expiry={expiry}"

        self._log(f"DoodStream: URL final -> {final_stream}")
        return final_stream

    def _dood_pass_request(self, pass_url, referer, seed_cookies):
        try:
            headers = {
                "Range": "bytes=0-",
                "Referer": referer,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
            }

            if self.headers and "User-Agent" in self.headers:
                headers["User-Agent"] = self.headers["User-Agent"]
            else:
                headers["User-Agent"] = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                )

            domain = urlparse(referer).netloc
            for name, value in seed_cookies.items():
                try:
                    self.session.cookies.set(
                        name, value, domain=domain, path="/"
                    )
                except Exception:
                    pass

            resp = self.session.get(
                pass_url,
                headers=headers,
                allow_redirects=True,
                timeout=30,
            )

            if resp.status_code != 200:
                self._log(f"DoodStream: status {resp.status_code}")
                return None

            txt = resp.text.strip()
            if not txt:
                return None
            if txt == "RELOAD":
                return None
            if txt.startswith("<"):
                return None
            if not txt.startswith("http"):
                self._log(f"DoodStream: respuesta no-URL: {txt[:80]!r}")
                return None

            return txt
        except Exception as e:
            self._log(f"DoodStream: request error -> {e}")
            return None

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
        unpacked = unpack_eval_script(script, debug=self.debug)
        if not unpacked:
            return None
        return self._extraer_m3u8(unpacked) or self._extraer_mp4(unpacked)

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
    #     ESTRATEGIA 6: Redirección interna
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
