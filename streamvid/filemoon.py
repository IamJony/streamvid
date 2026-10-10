#!/usr/bin/env python3
# Extractor para filemoon, sfastwish by IamJony

import sys
import re
import subprocess
import os
from requests_html import HTMLSession
from real_headers import real_headers

# Headers y User-agent aletorios
random_headers = real_headers()


class FileMoonExtractor:
    """Clase para extraer videos de FileMoon"""

    def __init__(self, session=None, temp_file='/tmp/eval.js', debug=False):
        self.session = session or HTMLSession()
        self.temp_file = temp_file
        self.debug = debug

    def _log(self, msg, level="info"):
        if not self.debug:
            return
        icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
        print(f"[filemoon] {icons.get(level, '·')} {msg}", file=sys.stderr)

    def obtener_html(self, url):
        self._log(f"descargando: {url}", "step")
        try:
            response = self.session.get(url, headers=random_headers)
            response.raise_for_status()
            self._log(f"HTML obtenido ({len(response.text)} bytes)", "ok")
            return response.text
        except Exception as e:
            self._log(f"error de descarga: {e}", "fail")
            raise Exception(f"Error al descargar la página: {e}")

    def buscar_script_eval(self, html):
        self._log("buscando script con eval(function...)", "step")
        script_pattern = r'<script[^>]*type=[\'"]text/javascript[\'"][^>]*>.*?eval\(function\(p,a,c,k,e,d\).*?</script>'
        script_match = re.search(script_pattern, html,
                                 re.DOTALL | re.IGNORECASE)

        if script_match:
            self._log("script eval encontrado", "ok")
            return script_match.group()

        self._log("no se encontró script eval", "warn")
        return None

    def guardar_script(self, script_contenido):
        self._log(f"guardando script en {self.temp_file}", "step")
        try:
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                f.write(script_contenido)
            self._log("script guardado", "ok")
            return True
        except Exception as e:
            self._log(f"error al guardar: {e}", "fail")
            raise Exception(f"Error al guardar script: {e}")

    def ejecutar_eval_unpack(self):
        self._log("ejecutando eval-unpacker", "step")
        try:
            resultado = subprocess.run(['eval-unpacker', self.temp_file],
                                       capture_output=True,
                                       text=True,
                                       check=True)
            self._log(f"eval-unpack OK ({len(resultado.stdout)} bytes)", "ok")
            return resultado.stdout
        except subprocess.CalledProcessError as e:
            self._log(f"eval-unpacker falló: {e.stderr}", "fail")
            raise Exception(f"Error al ejecutar eval-unpack: {e.stderr}")
        except FileNotFoundError:
            self._log("eval-unpacker no encontrado", "fail")
            raise Exception("No se encuentra 'eval-unpack'. ¿Está instalado?")

    def extraer_video_link(self, texto):
        self._log("buscando enlace m3u8 en el texto", "step")

        master_pattern = r'(https?://[^"\'\s]+master\.m3u8[^"\'\s]*)'
        master_match = re.search(master_pattern, texto)

        if master_match:
            enlace = master_match.group(1)
            self._log(f"master.m3u8 encontrado: {enlace}", "ok")
            return enlace

        m3u8_pattern = r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)'
        m3u8_match = re.search(m3u8_pattern, texto)

        if m3u8_match:
            enlace = m3u8_match.group(1)
            self._log(f".m3u8 alternativo encontrado: {enlace}", "ok")
            return enlace

        self._log("no se encontró ningún .m3u8", "warn")
        return None

    def limpiar_temp(self):
        try:
            if os.path.exists(self.temp_file):
                os.remove(self.temp_file)
                self._log(f"temp eliminado: {self.temp_file}")
        except Exception:
            pass

    def extraer(self, url):
        try:
            html = self.obtener_html(url)

            script = self.buscar_script_eval(html)
            if not script:
                raise Exception("No se encontró el script con eval")

            self.guardar_script(script)
            unpacked = self.ejecutar_eval_unpack()
            video_link = self.extraer_video_link(unpacked)

            if not video_link:
                raise Exception("No se pudo encontrar el enlace del video")

            self._log(f"extracción completada: {video_link}", "ok")
            return video_link

        finally:
            self.limpiar_temp()

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

    extractor = FileMoonExtractor(debug=debug)
    extractor.extraer_y_mostrar(url)


if __name__ == "__main__":
    main()
