# Uso como librería Streamvid.

## Instalación

```bash
pip install -e .
```

## Imports

Todos los extractores se pueden importar desde la raíz del paquete:

```python
from streamvid import (
    FileMoonExtractor,
    MP4UploadExtractor,
    OkRuExtractor,
    StreamtapeExtractor,
    UniversalExtractor,
    VoeExtractor,
    EXTRACTORS,
)
```

## `EXTRACTORS`

Lista con todas las clases de extractores registrados. `UniversalExtractor`
está siempre al final porque actúa como fallback.

```python
from streamvid import EXTRACTORS

for cls in EXTRACTORS:
    print(cls.__name__)
```

Salida:

```
FileMoonExtractor
MP4UploadExtractor
OkRuExtractor
StreamtapeExtractor
VoeExtractor
UniversalExtractor
```

Útil para autodetección:

```python
def detectar(url):
    for cls in EXTRACTORS:
        if cls().soporta(url):
            return cls
    return None
```

## Interfaz de un extractor

Todos los extractores exponen exactamente los mismos métodos:

```python
extractor = XxxExtractor(session=None, debug=False)

extractor.soporta(url)   # → bool
extractor.extraer(url)   # → str | None, lanza excepción si falla
```

### `soporta(url)`

Devuelve `True` si el extractor puede manejar esa URL. **No hace peticiones
HTTP**, es solo una comprobación de dominio/patrón.

```python
from streamvid import VoeExtractor

VoeExtractor().soporta("https://voe.sx/e/abc")     # True
VoeExtractor().soporta("https://youtube.com/x")    # False
```

`UniversalExtractor.soporta()` siempre devuelve `True`.

### `extraer(url)`

Devuelve el enlace del video o lanza excepción si falla.

```python
from streamvid import VoeExtractor

link = VoeExtractor().extraer("https://voe.sx/e/abc")
```

Si el video no existe, el sitio cambió, o hay cualquier otro error, se
lanza una excepción con mensaje descriptivo.

### `debug`

Si pasas `debug=True` al constructor, el extractor imprime logs a `stderr`
con prefijo `[nombre]`:

```python
from streamvid import FileMoonExtractor

extractor = FileMoonExtractor(debug=True)
extractor.extraer("https://filemoon.sx/e/abc")
```

### `session`

Puedes inyectar una sesión HTTP propia para reutilizar cookies, headers o
proxies:

```python
from requests_html import HTMLSession
from streamvid import FileMoonExtractor

session = HTMLSession()
extractor = FileMoonExtractor(session=session)
```

Si no pasas ninguna, cada extractor crea su propia `HTMLSession`.

## Ejemplos

### Extraer de un solo sitio

```python
from streamvid import FileMoonExtractor

try:
    link = FileMoonExtractor().extraer("https://filemoon.sx/e/abc")
    print(link)
except Exception as e:
    print(f"Fallo: {e}")
```

### Extraer con autodetección

```python
from streamvid import EXTRACTORS

def extraer(url):
    for cls in EXTRACTORS:
        try:
            extractor = cls()
            if extractor.soporta(url):
                return extractor.extraer(url)
        except Exception:
            continue
    return None

link = extraer("https://voe.sx/e/abc")
print(link)
```

### Procesar una lista de URLs

```python
from streamvid import EXTRACTORS

def extraer(url):
    for cls in EXTRACTORS:
        try:
            e = cls()
            if e.soporta(url):
                return e.extraer(url)
        except Exception:
            continue
    return None

urls = [
    "https://filemoon.sx/e/abc",
    "https://voe.sx/e/def",
    "https://streamtape.com/e/ghi",
]

for url in urls:
    link = extraer(url)
    print(f"{url} → {link}")
```

### Descargar con ffmpeg

```python
import subprocess
from streamvid import VoeExtractor

URL = "https://voe.sx/e/vnooybqweztc"
link = VoeExtractor().extraer(URL)

subprocess.run([
    "ffmpeg", "-i", link, "-c", "copy", "video.mp4"
])
```

### Integrarlo en una API Flask

```python
from flask import Flask, jsonify, request
from streamvid import EXTRACTORS

app = Flask(__name__)

def extraer(url):
    for cls in EXTRACTORS:
        try:
            e = cls()
            if e.soporta(url):
                return e.extraer(url)
        except Exception:
            continue
    return None

@app.route("/extract")
def extract():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "missing url"}), 400

    link = extraer(url)
    if not link:
        return jsonify({"error": "could not extract"}), 404

    return jsonify({"url": url, "link": link})
```

## Errores comunes

| Error | Causa |
|---|---|
| `ImportError: No module named streamvid` | `pip install -e .` no ejecutado |
| `No se encontró el origen del video` | El sitio cambió o el video no existe |
| `404 Client Error` | El video fue borrado |
| `Error al descargar la página` | Problema de red o bloqueo del sitio |

Todos se lanzan como excepciones regulares. Captúralas con `try/except`.

## Añadir un extractor nuevo

Consulta [`extractores.md`](extractores.md).
