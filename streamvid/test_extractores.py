#!/usr/bin/env python3
# Script para comprobar el estado de los extractores de manera rapida IamJony

from requests_html import HTMLSession
from mp4upload import MP4UploadExtractor
from filemoon import FileMoonExtractor
from voe import VoeExtractor
from streamtape import StreamtapeExtractor
from universal import UniversalExtractor
from ok import OkRuExtractor

print("PRUEBA DE EXTRACTORES\n")

# URLs de prueba por servidor
urls = {
    "MP4Upload": "https://www.mp4upload.com/embed-882s1404awa2.html",
    "Streamtape": "https://streamtape.com/e/jpYjkraO4ZhzVZk/01.mp4",
    "FileMoon": "https://sfastwish.com/e/t0skqlzi01j0",
    "Voe": "https://voe.sx/e/vnooybqweztc",
    "Lulu": "https://luluvdo.com/e/k60tod6pn7zk",
    "OkRu": "https://ok.ru/videoembed/6127798127135"
}

session = HTMLSession()

# Fase 1: comprobar que las URLs responden por HTTP
print("--- Estado HTTP de las URLs de prueba ---")
for servidor, url in urls.items():
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            print(f"{servidor}: {response.status_code} OK")
        else:
            print(f"{servidor}: Estado inesperado ({response.status_code})")
    except Exception as e:
        print(f"{servidor}: Error de conexión ({e})")

print("\n--- Prueba de extracción ---")

# Guarda el resultado (True/False) de cada extractor
resultados = {}


def probar(nombre, funcion):
    """Ejecuta un extractor y clasifica el resultado en LIVE/VACIO/DEAD."""
    try:
        r = funcion()
        if r:
            print(f"{nombre}: LIVE")
            resultados[nombre] = True
        else:
            print(f"{nombre}: VACIO")
            resultados[nombre] = False
    except Exception as e:
        print(f"{nombre}: DEAD ({e})")
        resultados[nombre] = False


# Fase 2: probar cada extractor con su URL

probar("MP4Upload", lambda: MP4UploadExtractor().extraer(urls["MP4Upload"]))

probar("Streamtape", lambda: StreamtapeExtractor().extraer(urls["Streamtape"]))

probar("FileMoon", lambda: FileMoonExtractor().extraer(urls["FileMoon"]))

probar("OkRu", lambda: OkRuExtractor().extraer(urls["OkRu"]))


def extraer_voe():
    """VOE necesita dos pasos: obtener HTML y luego extraer src."""
    v = VoeExtractor()
    c = v.obtener_contenido(urls["Voe"])
    return v.extraer_video_src(c)


probar("Voe", extraer_voe)


def extraer_universal(url):
    """Universal recibe la URL directamente."""
    u = UniversalExtractor()
    return u.extraer(url)


probar("Universal (Lulu)", lambda: extraer_universal(urls["Lulu"]))

# Fase 3: resumen final
total = len(resultados)
live = sum(1 for v in resultados.values() if v)

print(f"\nRESUMEN: {live}/{total} extractores funcionando")
