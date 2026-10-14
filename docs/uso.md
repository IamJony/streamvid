# Referencia de la CLI

## Sintaxis

```
streamvid [--extractor EXTRACTOR] [--debug] [--info] [--list] [--test] [--headers] <URL>
```

## Argumentos posicionales

### `<URL>`

URL del video embebido del que extraer el enlace.

```bash
streamvid "https://filemoon.sx/e/abc123"
```

Opcional si usas `--list` o `--test`.

---

## Opciones

### `-e, --extractor <nombre>`

Fuerza el uso de un extractor concreto en vez de autodetectarlo por dominio.

```bash
streamvid -e voe "https://voe.sx/e/abc123"
```

Valores posibles:

```
mp4upload
streamtape
filemoon
voe
okru
universal
```

Útil cuando:

- La autodetección falla
- Quieres probar el extractor `universal` en una URL que tiene su propio extractor
- Un dominio aloja contenido de otro servicio

### `-d, --debug`

Activa el logging detallado. Los mensajes van a `stderr`, nunca a `stdout`.

```bash
streamvid --debug "https://filemoon.sx/e/abc123"
```

Salida típica:

```
[filemoon] → descargando: https://filemoon.sx/e/abc123
[filemoon] ✔ HTML obtenido (45678 bytes)
[filemoon] → buscando script con eval(function...)
[filemoon] ✔ script eval encontrado
[filemoon] → guardando script en /tmp/eval.js
[filemoon] → ejecutando eval-unpacker
[filemoon] ✔ eval-unpack OK (1234 bytes)
[filemoon] → buscando enlace m3u8 en el texto
[filemoon] ✔ master.m3u8 encontrado: https://cdn.filemoon.sx/.../master.m3u8
[filemoon] ✔ extracción completada: https://cdn.filemoon.sx/.../master.m3u8
```

Como va a `stderr`, puedes separar el enlace limpio de los logs:

```bash
streamvid --debug "$URL" 2>debug.log >link.txt
```

### `-i, --info`

Muestra información adicional antes de extraer: qué extractor se usó y la URL
original.

```bash
streamvid --info "https://filemoon.sx/e/abc123"
```

Salida:

```
Info: Using extractor: FileMoon
Info: URL: https://filemoon.sx/e/abc123

✓ FileMoon: FOUND
  URL: https://cdn.filemoon.sx/.../master.m3u8
```

Si falla, muestra el error en formato legible:

```
✗ FileMoon: ERROR
  No se encontró el origen del video
```

### `-l, --list`

Lista los extractores disponibles junto a un ejemplo de URL.

```bash
streamvid --list
```

Salida:

```
AVAILABLE SERVERS:

  mp4upload https://www.mp4upload.com/embed-9lxsg2qkoclq.html
  streamtape https://streamtape.com/e/jpYjkraO4ZhzVZk/01.mp4
  filemoon https://sfastwish.com/e/t0skqlzi01j0
  voe https://voe.sx/e/vnooybqweztc
  okru https://ok.ru/videoembed/6127798127135
  universal https://luluvdo.com/e/k60tod6pn7zk
```

No requiere URL.

### `-t, --test`

Ejecuta un **autotest offline** que verifica:

- El paquete `streamvid` se importa correctamente
- Los extractores están registrados
- Cada clase se puede instanciar sin errores

**No toca la red.** No prueba URLs reales.

```bash
streamvid --test
```

Salida:

```
Info: Autotest offline de extractores...

  ✓ MP4Upload
  ✓ Streamtape
  ✓ FileMoon
  ✓ Voe
  ✓ OkRu
  ✓ Universal

6/6 extractores válidos
```

Útil para verificar una instalación sin depender de que los sitios externos
estén disponibles.

### `--headers`

Imprime los headers HTTP que el CDN espera para servir el video, junto con el
enlace. Esencial para reproducir con mpv, ffmpeg o yt-dlp cuando el CDN exige
un `Referer` concreto.

```bash
streamvid --headers "https://luluvdo.com/e/k60tod6pn7zk"
```

Salida:

```
# User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...
# Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
# Accept-Language: en-US,en;q=0.9
# Referer: https://luluvdo.com/
https://puyjwh3anu5e.tnmr.org/hls2/03/04455/k60tod6pn7zk_h/master.m3u8?t=...
```

Las líneas con `# ` son comentarios válidos para bash. El enlace va al final,
sin prefijo. Así puedes hacer pipes sin que los headers rompan la salida.

#### ¿Cuándo usar `--headers`?

Cuando el CDN devuelve `403 Forbidden` al abrir el enlace directamente, o
cuando pasas el enlace a un reproductor y no arranca:

```bash
# Sin headers → 403 o nada
streamvid "$URL" | xargs mpv

# Con headers → reproduce
streamvid --headers "$URL"
```

#### Integración con mpv

```bash
OUT=$(streamvid --headers "$URL" 2>/dev/null)
LINK=$(echo "$OUT" | grep -v '^#')
UA=$(echo "$OUT" | grep '^# User-Agent:' | cut -d' ' -f3-)
REF=$(echo "$OUT" | grep '^# Referer:' | cut -d' ' -f3)

mpv --user-agent="$UA" --referrer="$REF" "$LINK"
```

#### Integración con ffmpeg

```bash
OUT=$(streamvid --headers "$URL" 2>/dev/null)
LINK=$(echo "$OUT" | grep -v '^#')
REF=$(echo "$OUT" | grep '^# Referer:' | cut -d' ' -f3)
UA=$(echo "$OUT" | grep '^# User-Agent:' | cut -d' ' -f3-)

ffmpeg -headers "Referer: $REF\r\nUser-Agent: $UA\r\n" -i "$LINK" -c copy out.mp4
```

#### Integración con VLC

VLC no acepta `--referrer` por CLI, así que se necesita un archivo `.m3u`
temporal con los headers embebidos. El script `scripts/play.py` del repo
hace esto automáticamente.

#### Solo el Referer

```bash
streamvid --headers "$URL" 2>/dev/null | grep '^# Referer:' | cut -d' ' -f3
```

Salida:

```
https://luluvdo.com/
```

#### Solo el link (ignorando los headers)

```bash
streamvid --headers "$URL" 2>/dev/null | grep -v '^#'
```

#### Nota

Si un extractor no implementa `obtener_headers()`, el flag simplemente se
ignora y solo se imprime el link. No rompe nada.

### `-h, --help`

Muestra la ayuda completa.

```bash
streamvid --help
```

---

## Códigos de salida

| Código | Significado                                            |
| ------ | ------------------------------------------------------ |
| `0`    | Éxito: enlace extraído y mostrado en `stdout`          |
| `1`    | Fallo: no se pudo extraer, URL inválida o error de red |

Ejemplo en scripts:

```bash
if streamvid "$URL" > link.txt; then
    echo "OK: $(cat link.txt)"
else
    echo "Fallo al extraer"
fi
```

---

## Comportamiento de salida

- **Éxito** → solo el enlace en `stdout`, exit `0`
- **Fallo sin `--debug`** → nada en `stdout`, exit `1`
- **Fallo con `--debug`** → logs en `stderr` con el detalle del error
- **Con `--info`** → mensajes informativos en `stdout` + el enlace
- **Con `--headers`** → cabeceras con `# ` + enlace

Eso permite usar Streamvid en pipes:

```bash
streamvid "$URL" | xargs mpv
```

Y con headers:

```bash
streamvid --headers "$URL" 2>/dev/null | grep -v '^#' | xargs mpv
```

---

## Combinaciones útiles

### Solo el enlace, sin errores

```bash
streamvid "$URL" 2>/dev/null
```

### Extraer y guardar el log completo

```bash
streamvid --debug "$URL" 2>log.txt >link.txt
```

### Forzar extractor y ver qué hace

```bash
streamvid -e universal --debug "$URL"
```

### Ver todo el detalle posible

```bash
streamvid --info --debug "$URL"
```

### Con headers (para CDN que exigen Referer)

```bash
streamvid --headers "$URL"
```

### Headers + debug (para depurar problemas de reproducción)

```bash
streamvid --headers --debug "$URL"
```

### Solo el Referer

```bash
streamvid --headers "$URL" 2>/dev/null | grep '^# Referer:' | cut -d' ' -f3
```

### Comprobar la instalación sin red

```bash
streamvid --test && echo "Instalación OK"
```

### Procesar varias URLs en un bucle

```bash
for url in "https://voe.sx/e/abc" "https://filemoon.sx/e/def"; do
    echo "Procesando: $url"
    streamvid "$url" 2>/dev/null || echo "Fallo"
done
```

### Procesar varias URLs y guardar headers por cada una

```bash
for url in "https://voe.sx/e/abc" "https://luluvdo.com/e/xyz"; do
    echo "=== $url ==="
    streamvid --headers "$url"
    echo
done
```

### Alias para reproducir con mpv automáticamente

Añade esto a tu `~/.bashrc`:

```bash
svplay() {
    local out link ref ua
    out=$(streamvid --headers "$1" 2>/dev/null) || { echo "Fallo al extraer"; return 1; }
    link=$(echo "$out" | grep -v '^#')
    ref=$(echo "$out" | grep '^# Referer:' | cut -d' ' -f3)
    ua=$(echo "$out" | grep '^# User-Agent:' | cut -d' ' -f3-)
    mpv --user-agent="$ua" --referrer="$ref" "$link"
}
```

Y luego:

```bash
svplay "https://luluvdo.com/e/k60tod6pn7zk"
```

---

## Uso desde Python

Equivalentes a los comandos anteriores:

```python
from streamvid import cli

cli.main(["--list"])
cli.main(["--test"])
cli.main(["https://filemoon.sx/e/abc"])
cli.main(["-e", "voe", "--debug", "https://voe.sx/e/abc"])
cli.main(["--headers", "https://luluvdo.com/e/k60tod6pn7zk"])
cli.main(["--headers", "--debug", "https://luluvdo.com/e/k60tod6pn7zk"])
```

Útil para invocar el CLI desde otro script sin usar `subprocess`.
