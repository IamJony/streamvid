# Streamvid

Extractor HLS de videos embebidos. Soporta múltiples plataformas.

## Plataformas soportadas

| Extractor | Estado |
|---|---|
| MP4Upload | ✅ |
| Streamtape | ✅ |
| Filemoon | ✅ |
| Voe | ✅ |
| OK (OkRu) | ✅ |
| Universal | ✅ (luvdo, etc.) |

## Instalación

### Opción 1 — Desde PyPI (recomendado)

```bash
pip install streamvid
```

### Opción 2 — Instalación rápida desde los releases

Descarga los dos wheels e instálalos. **Es imprescindible instalar también `eval_unpacker`**, ya que varios extractores lo usan para desofuscar el JavaScript embebido en las páginas; sin él, la mayoría de extractores fallarán.

```bash
pip install \
  https://github.com/IamJony/streamvid/releases/download/1.0/streamvid-1.0.0-py3-none-any.whl \
  https://github.com/IamJony/streamvid/releases/download/1.0/eval_unpacker-0.1.0-py3-none-any.whl
```

> ⚠️ **Nota:** sin `eval_unpacker` los extractores MP4Upload, Filemoon, Voe, OK y Universal no podrán resolver el stream HLS, porque dependen de él para desempaquetar el JavaScript ofuscado (tipo `eval(function(p,a,c,k,e,d){...})`) que contienen esas páginas.

## Uso

### Como librería

```python
from streamvid import MP4UploadExtractor

resultado = MP4UploadExtractor().extraer(
    "https://www.mp4upload.com/embed-882s1404awa2.html"
)
print(resultado)
```

También puedes importar los extractores desde sus módulos individuales:

```python
from mp4upload import MP4UploadExtractor
from filemoon import FileMoonExtractor
from voe import VoeExtractor
from streamtape import StreamtapeExtractor
from universal import UniversalExtractor
from ok import OkRuExtractor

resultado = MP4UploadExtractor().extraer(
    "https://www.mp4upload.com/embed-882s1404awa2.html"
)
print(resultado)
```

### Línea de comandos

```bash
streamvid <url>
```

O directamente como módulo:

```bash
python -m streamvid.main <url>
```

## Extractores disponibles

| Clase | Módulo | Servicio |
|---|---|---|
| `MP4UploadExtractor` | `mp4upload` | mp4upload.com |
| `StreamtapeExtractor` | `streamtape` | streamtape.com |
| `FileMoonExtractor` | `filemoon` | filemoon.sx |
| `VoeExtractor` | `voe` | voe.sx |
| `OkRuExtractor` | `ok` | ok.ru |
| `UniversalExtractor` | `universal` | luvdo, y otros |

## Desarrollo

Clonar el repositorio e instalar en modo editable:

```bash
git clone https://github.com/IamJony/streamvid.git
cd streamvid
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install eval_unpacker
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
pip install \
  dist/streamvid-1.0.0-py3-none-any.whl \
  https://github.com/IamJony/streamvid/releases/download/1.0/eval_unpacker-0.1.0-py3-none-any.whl
streamvid --help
```

## Dependencias

Runtime (declaradas en `install_requires`):

- `requests_html`
- `real_headers`
- `lxml_html_clean`
- `eval_unpacker` *(necesario para desempaquetar JavaScript ofuscado en la mayoría de extractores)*

## Requisitos

- Python 3.8 o superior

## Licencia

MIT
