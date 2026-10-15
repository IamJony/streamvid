# Uso como librería Streamvid

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
    MixdropExtractor,
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

extractor.soporta(url)          # → bool
extractor.extraer(url)          # → str | None, lanza excepción si falla
extractor.obtener_headers()     # → dict | None (solo tras extraer)
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

### `obtener_headers()`

Devuelve los headers HTTP que el CDN espera para servir el video. Incluye
el `Referer` correcto (el dominio final tras redirects) y el `User-Agent`
que se usó al pedir el HTML.

**Disponible solo después de llamar a `extraer()`.** Antes devuelve `None`.

```python
from streamvid import UniversalExtractor

extractor = UniversalExtractor()

print(extractor.obtener_headers())     # → None (aún no se ha extraído)

link = extractor.extraer("https://luluvdo.com/e/k60tod6pn7zk")

headers = extractor.obtener_headers()
print(headers)
```

Salida:

```python
{
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://luluvdo.com/'
}
```

#### ¿Por qué son necesarios los headers?

Muchos CDN de video rechazan peticiones sin el `Referer` correcto
(devolviendo `403 Forbidden`). Como los sitios redirigen a dominios aleatorios
que cambian por sesión, no sirve hardcodear el Referer. `obtener_headers()`
resuelve esto automáticamente: devuelve el dominio **real** desde el que se
sirvió el HTML tras seguir todas las redirecciones.

#### Cómo usarlos

**Con mpv:**

```python
import subprocess
from streamvid import UniversalExtractor

extractor = UniversalExtractor()
link = extractor.extraer("https://luluvdo.com/e/k60tod6pn7zk")
headers = extractor.obtener_headers() or {}

subprocess.run([
    "mpv",
    f"--user-agent={headers.get('User-Agent', '')}",
    f"--referrer={headers.get('Referer', '')}",
    link,
])
```

**Con ffmpeg:**

```python
import subprocess
from streamvid import UniversalExtractor

extractor = UniversalExtractor()
link = extractor.extraer(url)
headers = extractor.obtener_headers() or {}

# ffmpeg acepta varios headers separados por \r\n
header_str = "".join(f"{k}: {v}\r\n" for k, v in headers.items())

subprocess.run([
    "ffmpeg",
    "-headers", header_str,
    "-i", link,
    "-c", "copy",
    "video.mp4",
])
```

**Con yt-dlp:**

```python
import subprocess
from streamvid import UniversalExtractor

extractor = UniversalExtractor()
link = extractor.extraer(url)
headers = extractor.obtener_headers() or {}

subprocess.run([
    "yt-dlp",
    "--user-agent", headers.get("User-Agent", ""),
    "--referer", headers.get("Referer", ""),
    link,
])
```

**Con requests (descarga manual):**

```python
import requests
from streamvid import UniversalExtractor

extractor = UniversalExtractor()
link = extractor.extraer(url)
headers = extractor.obtener_headers() or {}

r = requests.get(link, headers=headers, stream=True)
with open("video.ts", "wb") as f:
    for chunk in r.iter_content(chunk_size=8192):
        f.write(chunk)
```

#### Imprimir solo el Referer

Si solo necesitas el Referer:

```python
referer = extractor.obtener_headers().get("Referer")
print(referer)
```

#### Nota sobre el orden

`obtener_headers()` **solo funciona después de `extraer()`**, porque necesita
la respuesta HTTP para calcular el dominio final:

```python
extractor = UniversalExtractor()

# ❌ mal: aún no hay headers
print(extractor.obtener_headers())   # → None

# ✅ bien: primero extraer
link = extractor.extraer(url)
headers = extractor.obtener_headers()
```

Si encadenas todo en una línea pierdes la referencia al extractor:

```python
# ❌ mal: no puedes consultar headers después
link = UniversalExtractor().extraer(url)

# ✅ bien: guarda el extractor en una variable
extractor = UniversalExtractor()
link = extractor.extraer(url)
headers = extractor.obtener_headers()
```

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

### Extraer con autodetección + headers

```python
from streamvid import EXTRACTORS

def extraer_con_headers(url):
    for cls in EXTRACTORS:
        try:
            extractor = cls()
            if not extractor.soporta(url):
                continue

            link = extractor.extraer(url)
            headers = None
            if hasattr(extractor, "obtener_headers"):
                headers = extractor.obtener_headers()

            return link, headers
        except Exception:
            continue
    return None, None

link, headers = extraer_con_headers("https://luluvdo.com/e/k60tod6pn7zk")
print(f"Link:    {link}")
print(f"Headers: {headers}")
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

### Descargar con ffmpeg (con headers)

```python
import subprocess
from streamvid import VoeExtractor

URL = "https://voe.sx/e/vnooybqweztc"

extractor = VoeExtractor()
link = extractor.extraer(URL)
headers = extractor.obtener_headers() or {}

header_str = "".join(f"{k}: {v}\r\n" for k, v in headers.items())

subprocess.run([
    "ffmpeg",
    "-headers", header_str,
    "-i", link,
    "-c", "copy",
    "video.mp4",
])
```

### Reproducir con mpv (con headers)

```python
import subprocess
from streamvid import EXTRACTORS

URL = "https://luluvdo.com/e/k60tod6pn7zk"

for cls in EXTRACTORS:
    extractor = cls()
    if not extractor.soporta(URL):
        continue

    link = extractor.extraer(URL)
    headers = extractor.obtener_headers() if hasattr(extractor, "obtener_headers") else None

    cmd = ["mpv"]
    if headers:
        if headers.get("User-Agent"):
            cmd.append(f"--user-agent={headers['User-Agent']}")
        if headers.get("Referer"):
            cmd.append(f"--referrer={headers['Referer']}")
    cmd.append(link)

    subprocess.run(cmd)
    break
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
            if not e.soporta(url):
                continue

            link = e.extraer(url)
            headers = e.obtener_headers() if hasattr(e, "obtener_headers") else None

            return {
                "extractor": cls.__name__,
                "url": link,
                "headers": headers,
            }
        except Exception:
            continue
    return None

@app.route("/extract")
def extract():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "missing url"}), 400

    info = extraer(url)
    if not info:
        return jsonify({"error": "could not extract"}), 404

    return jsonify(info)
```

Petición:

```bash
curl "http://localhost:5000/extract?url=https://luluvdo.com/e/k60tod6pn7zk"
```

Respuesta:

```json
{
    "extractor": "UniversalExtractor",
    "url": "https://puyjwh3anu5e.tnmr.org/hls2/03/04455/k60tod6pn7zk_h/master.m3u8?t=...",
    "headers": {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ...",
        "Accept": "text/html,...",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://luluvdo.com/"
    }
}
```

## Errores comunes

| Error                                    | Causa                                |
| ---------------------------------------- | ------------------------------------ |
| `ImportError: No module named streamvid` | `pip install -e .` no ejecutado      |
| `No se encontró el origen del video`     | El sitio cambió o el video no existe |
| `404 Client Error`                       | El video fue borrado                 |
| `Error al descargar la página`           | Problema de red o bloqueo del sitio  |
| `obtener_headers()` devuelve `None`      | Se llamó antes de `extraer()`        |

Todos se lanzan como excepciones regulares. Captúralas con `try/except`.

## Añadir un extractor nuevo

Consulta [`extractores.md`](extractores.md).
