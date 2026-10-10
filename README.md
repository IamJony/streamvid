# Streamvid

Extractor HLS de videos embebidos. Soporta múltiples plataformas.

## Plataformas soportadas

| Extractor | Estado |
|---|---|
| MP4Upload | ✅ |
| Streamtape | ✅ |
| Filemoon | ✅ |
| Voe | ✅ |
| OK | ✅ |
| Universal | ✅ (luvdo, etc.) |

## Instalación

```bash
pip install streamvid
```

## Uso

### Línea de comandos

```bash
streamvid <url>
```

O directamente como módulo:

```bash
python -m streamvid.main <url>
```

### Como librería

```python
from streamvid import extract

url = "https://example.com/embed/xxxxx"
hls_url = extract(url)
print(hls_url)
```

## Desarrollo

Clonar el repositorio e instalar en modo editable:

```bash
git clone https://github.com/IamJony/streamvid.git
cd streamvid
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Construir el paquete

```bash
python -m build
```

Genera `dist/streamvid-1.0.0.tar.gz` y `dist/streamvid-1.0.0-py3-none-any.whl`.

### Probar la instalación en un entorno limpio

```bash
python -m venv /tmp/test_streamvid
source /tmp/test_streamvid/bin/activate
pip install dist/streamvid-1.0.0-py3-none-any.whl
streamvid --help
```

## Dependencias

- `requests_html`
- `real_headers`
- `lxml_html_clean`

## Requisitos

- Python 3.8 o superior

## Licencia

MIT
