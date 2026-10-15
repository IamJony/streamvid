#!/usr/bin/env python3
# Extractor para mixdrop by IamJony

import sys
import re
import subprocess
import os
from urllib.parse import urlparse
from requests_html import HTMLSession
from real_headers import real_headers


class MixdropExtractor:
    """Clase para extraer videos de Mixdrop

    Técnica: el reproductor embebe un script ofuscado con el packer
    de Dean Edwards (eval(function(p,a,c,k,e,d)...)) junto a otras
    declaraciones MDCore (ref, sublangs, etc.). Se aísla el bloque
    <script> completo, se guarda en un temporal y se desempaca con
    'eval-unpacker'.

    Tras desempacar se reconstruye MDCore.wurl, que apunta al MP4
    progresivo (no HLS) servido desde dominios tipo mxcontent.net
    con parámetros de expiración (?s=...&e=...&_t=...).
    """

    # Dominios soportados
    DOMINIOS = ("mxdrop", "mixdrop")

    def __init__(self, session=None, temp_file='/tmp/mixdrop_eval.js', debug=False):
        self.session = session or HTMLSession()
        self.temp_file = temp_file
        self.debug = debug
        self.headers = None

    # ---------- API pública ----------

    def soporta(self, url: str) -> bool:
        return any(dominio in url for dominio in self.DOMINIOS)

    def extraer(self, url):
        try:
            html = self._obtener_html(url)

            script = self._buscar_script_eval(html)
            if not script:
                raise Exception("No se encontró el script con eval")

            self._guardar_script(script)
            unpacked = self._ejecutar_eval_unpack()
            video_link = self._extraer_video_link(unpacked)

            if not video_link:
                raise Exception("No se pudo encontrar el enlace del video")

            if not self._es_link_valido(video_link):
                raise Exception(f"El enlace extraído no es válido: {video_link}")

            self._log(f"extracción completada: {video_link}", "ok")
            return video_link
        except Exception as e:
            self._log(f"error fatal: {e}", "fail")
            raise
        finally:
            self._limpiar_temp()

    def extraer_y_mostrar(self, url, mostrar_headers=False):
        """Uso standalone. Imprime el link (stdout) y, opcionalmente,
        los headers del CDN en formato -H (stderr)."""
        try:
            video_link = self.extraer(url)
            print(video_link)

            if mostrar_headers:
                headers = self.obtener_headers()
                if headers:
                    print("\n# Headers para el CDN:", file=sys.stderr)
                    for k, v in headers.items():
                        print(f'-H "{k}: {v}"', file=sys.stderr)
                else:
                    print("# Sin headers (extracción sin sesión válida)", file=sys.stderr)

            return video_link
        except Exception as e:
            if self.debug:
                print(f"[mixdrop] error: {e}", file=sys.stderr)
            sys.exit(1)

    def obtener_headers(self):
        """Headers exactos que el CDN espera. Disponible tras extraer()."""
        return dict(self.headers) if self.headers else None

    # ---------- Logging ----------

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[mixdrop] {icons.get(level, '·')} {msg}", file=sys.stderr)

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

    # ---------- Eval unpacker ----------

    def _buscar_script_eval(self, html):
        """Aísla el bloque <script> que contiene el packer de Dean Edwards.

        En Mixdrop el eval() no está solo: comparte <script> con otras
        declaraciones MDCore.ref, MDCore.sublangs, etc. Por eso capturamos
        el contenido completo del <script> que contiene el eval y lo
        pasamos tal cual a eval-unpacker (con las etiquetas <script>).
        """
        self._log("buscando script con eval(function...)", "step")

        script_pattern = (
            r'<script[^>]*>'
            r'(.*?eval\(function\(p,a,c,k,e,d\).*?)'
            r'</script>'
        )
        script_match = re.search(script_pattern, html, re.DOTALL | re.IGNORECASE)

        if script_match:
            self._log("script eval encontrado", "ok")
            return f"<script>{script_match.group(1)}</script>"

        self._log("no se encontró script eval", "warn")
        return None

    def _guardar_script(self, script_contenido):
        self._log(f"guardando script en {self.temp_file}", "step")
        try:
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                f.write(script_contenido)
            self._log("script guardado", "ok")
        except Exception as e:
            self._log(f"error al guardar: {e}", "fail")
            raise Exception(f"Error al guardar script: {e}")

    def _ejecutar_eval_unpack(self):
        self._log("ejecutando eval-unpacker", "step")
        try:
            resultado = subprocess.run(
                ['eval-unpacker', self.temp_file],
                capture_output=True, text=True, check=True
            )
            self._log(f"eval-unpack OK ({len(resultado.stdout)} bytes)", "ok")
            return resultado.stdout
        except subprocess.CalledProcessError as e:
            self._log(f"eval-unpacker falló: {e.stderr}", "fail")
            raise Exception(f"Error al ejecutar eval-unpack: {e.stderr}")
        except FileNotFoundError:
            self._log("eval-unpacker no encontrado", "fail")
            raise Exception("No se encuentra 'eval-unpacker'. ¿Está instalado?")

    # ---------- Extracción del link ----------

    def _extraer_video_link(self, texto):
        """Busca MDCore.wurl en el JS desempacado.

        Tras desempacar, el script reconstruye:
            MDCore.wurl="//a.deliveryXX.mxcontent.net/v2/<id>.mp4?s=...&e=...&_t=..."
        El protocolo puede venir relativo (//...) → normalizamos a https://.
        """
        self._log("buscando MDCore.wurl en el texto desempacado", "step")

        # 1) Patrón principal: MDCore.wurl="..."
        wurl_pattern = r'MDCore\.wurl\s*=\s*["\']([^"\']+)["\']'
        wurl_match = re.search(wurl_pattern, texto)
        if wurl_match:
            enlace = wurl_match.group(1)
            if enlace.startswith("//"):
                enlace = "https:" + enlace
            self._log(f"wurl encontrado: {enlace}", "ok")
            return enlace

        # 2) Fallback: MP4 directo en el JS
        mp4_pattern = r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']'
        mp4_match = re.search(mp4_pattern, texto)
        if mp4_match:
            enlace = mp4_match.group(1)
            self._log(f".mp4 alternativo encontrado: {enlace}", "ok")
            return enlace

        # 3) Fallback: master.m3u8 (por si algún día sirven HLS)
        m3u8_pattern = r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)'
        m3u8_match = re.search(m3u8_pattern, texto)
        if m3u8_match:
            enlace = m3u8_match.group(1)
            self._log(f".m3u8 alternativo encontrado: {enlace}", "ok")
            return enlace

        self._log("no se encontró ningún enlace de video", "warn")
        return None

    # ---------- Validación ----------

    def _es_link_valido(self, link):
        if not link or not re.match(r'https?://', link):
            return False
        if re.search(
            r'\.(png|jpg|jpeg|gif|svg|ico|css|js|woff2?)(\?|$)', link, re.I
        ):
            return False
        return bool(re.search(r'\.(mp4|m3u8)(\?|$)', link, re.I))

    # ---------- Limpieza ----------

    def _limpiar_temp(self):
        try:
            if os.path.exists(self.temp_file):
                os.remove(self.temp_file)
                self._log(f"temp eliminado: {self.temp_file}")
        except Exception:
            pass


def _main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    debug = '--debug' in sys.argv or '-d' in sys.argv
    mostrar_headers = '--headers' in sys.argv

    if not args:
        if debug:
            print("Error: URL no proporcionada", file=sys.stderr)
            print(f"Uso: {sys.argv[0]} [--debug] [--headers] <URL>", file=sys.stderr)
        sys.exit(1)

    extractor = MixdropExtractor(debug=debug)
    extractor.extraer_y_mostrar(args[0], mostrar_headers=mostrar_headers)


if __name__ == "__main__":
    _main()
