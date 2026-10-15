# Streamvid

Extractor HLS de videos embebidos soporta múltiples plataformas de streaming.

[Estado de los extractores](https://iamjony.github.io/streamvid/status.html)

## ¿Qué es?

Streamvid es una **librería Python** que, dada la URL de un video embebido en
un servicio de streaming, obtiene el enlace directo al video (`.m3u8` o `.mp4`).

Está diseñado como **módulo** para integrarse en APIs, programas o scripts.
También incluye una CLI para uso directo desde la terminal.

## Extractores soportados

| Servicio             | Alias        | Ejemplo                                        |
| -------------------- | ------------ | ---------------------------------------------- |
| MP4Upload            | `mp4upload`  | `mp4upload.com/embed-xxxxx.html`               |
| Streamtape           | `streamtape` | `streamtape.com/e/xxxxx`                       |
| FileMoon             | `filemoon`   | `filemoon.sx/e/xxxxx`, `sfastwish.com/e/xxxxx` |
| Voé                  | `voe`        | `voe.sx/e/xxxxx`                               |
| OK.ru                | `okru`       | `ok.ru/videoembed/xxxxx`                       |
| Universal | `universal`  | Cualquier otro sitio (luluvdo, vidhidevip, doodstream)            |

## Instalación

### Dependencias

`streamvid` depende del paquete `eval-unpacker` para que funcionen los extractores. Este debe ser instalado de manera manual con el siguiente comando:

```bash
pip install https://github.com/IamJony/eval-unpacker/releases/download/eval_unpacker-0.1.0/eval_unpacker-0.1.0-py3-none-any.whl
```

## Clona el repositorio de streamvid

Requiere Python 3.8+.

```bash
git clone https://github.com/IamJony/streamvid.git
cd streamvid
pip install -e .
```

Esto instala el comando `streamvid` en tu PATH.

## Uso rápido

### Desde la terminal

```bash
# Extraer el enlace de un video
streamvid "https://filemoon.sx/e/abc123"

# Listar extractores disponibles
streamvid --list

# Ver ayuda
streamvid --help
```

### Como librería

```
from streamvid import FileMoonExtractor

extractor = FileMoonExtractor()
link = extractor.extraer("https://filemoon.sx/e/example")

print(link)
# https://cdn.filemoon.sx/hls2/.../master.m3u8
```



### Documentación

- **[Guía de uso](docs/uso.md)** — todo lo que puedes hacer con la CLI
- **[Uso como librería](docs/api.md)** — importar desde Python
- **[Crear un extractor](docs/extractores.md)** — guía para desarrolladores
- **[Como hacer tests](docs/test.md)** — guia para desarrolladores

## Estado de extractores

Los extractores dependen de servicios de terceros que cambian con frecuencia.
Un smoke test se ejecuta a diario para verificar que todos siguen funcionando.

Consulta el workflow en la pestaña [Actions](../../actions).

## Licencia

MIT
