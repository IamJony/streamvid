# Referencia de la CLI

## Sintaxis

```
streamvid [--extractor EXTRACTOR] [--debug] [--info] [--list] [--test] <URL>
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

### `-h, --help`

Muestra la ayuda completa.

```bash
streamvid --help
```

---

## Códigos de salida

| Código | Significado |
|---|---|
| `0` | Éxito: enlace extraído y mostrado en `stdout` |
| `1` | Fallo: no se pudo extraer, URL inválida o error de red |

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

Eso permite usar Streamvid en pipes:

```bash
streamvid "$URL" | xargs mpv
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

---

## Uso desde Python

Equivalentes a los comandos anteriores:

```python
from streamvid import cli

cli.main(["--list"])
cli.main(["--test"])
cli.main(["https://filemoon.sx/e/abc"])
cli.main(["-e", "voe", "--debug", "https://voe.sx/e/abc"])
```

Útil para invocar el CLI desde otro script sin usar `subprocess`.
