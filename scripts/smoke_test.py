#!/usr/bin/env python3
# Smoke test, prueba de extractores con url reales. by IamJony
#
# Uso:
#   python scripts/smoke_test.py
#
# Exit code:
#   0 → todos LIVE
#   1 → alguno DEAD / VACIO / fallo HTTP

import json
import sys
from pathlib import Path

import requests

from streamvid import (
    FileMoonExtractor,
    MP4UploadExtractor,
    OkRuExtractor,
    StreamtapeExtractor,
    UniversalExtractor,
    VoeExtractor,
)

EXTRACTOR_MAP = {
    "mp4upload":  MP4UploadExtractor,
    "streamtape": StreamtapeExtractor,
    "filemoon":   FileMoonExtractor,
    "voe":        VoeExtractor,
    "okru":       OkRuExtractor,
    "universal":  UniversalExtractor,
}

URLS_FILE = Path(__file__).parent / "urls.json"


def fase_http(urls):
    """Comprueba que las URLs responden por HTTP."""
    print("--- Estado HTTP ---")
    for nombre, url in urls.items():
        try:
            r = requests.get(url, timeout=10)
            status = "OK" if r.status_code == 200 else f"estado {r.status_code}"
            print(f"  {nombre:<12} {status}")
        except Exception as e:
            print(f"  {nombre:<12} error de conexión ({e})")


def probar(nombre, cls, url):
    """Ejecuta un extractor y clasifica el resultado."""
    try:
        resultado = cls(debug=False).extraer(url) if _acepta_debug(cls) else cls().extraer(url)
        if resultado:
            print(f"  {nombre:<12} LIVE")
            return True
        print(f"  {nombre:<12} VACIO")
        return False
    except Exception as e:
        print(f"  {nombre:<12} DEAD ({e})")
        return False


def _acepta_debug(cls):
    """Comprueba si el extractor acepta el kwarg debug."""
    import inspect
    try:
        sig = inspect.signature(cls.__init__)
        return "debug" in sig.parameters
    except (ValueError, TypeError):
        return False


def fase_extraccion(urls):
    print("\n--- Extracción ---")
    resultados = {}
    for nombre, url in urls.items():
        cls = EXTRACTOR_MAP.get(nombre)
        if cls is None:
            print(f"  {nombre:<12} (sin extractor, saltando)")
            continue
        resultados[nombre] = probar(nombre, cls, url)
    return resultados


def main():
    print("PRUEBA DE EXTRACTORES\n")

    urls = json.loads(URLS_FILE.read_text(encoding="utf-8"))

    fase_http(urls)
    resultados = fase_extraccion(urls)

    total = len(resultados)
    live = sum(1 for v in resultados.values() if v)
    print(f"\nRESUMEN: {live}/{total} extractores funcionando")

    return 0 if live == total else 1


if __name__ == "__main__":
    sys.exit(main())
