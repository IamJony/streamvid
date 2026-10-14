# Guía para crear un extractor

Criterios obligatorios que debe cumplir todo extractor de Streamvid.

---

## 1. Ubicación y nombre

```
src/streamvid/extractors/<nombre>.py
```

- Archivo dentro de `extractors/`, minúsculas, `snake_case`.
- Nombre = nombre real del servicio (`voe.py`, `okru.py`, `streamtape.py`).
- Clase: `<Nombre>Extractor` en `PascalCase`.

| Archivo         | Clase                 |
| --------------- | --------------------- |
| `voe.py`        | `VoeExtractor`        |
| `mp4upload.py`  | `MP4UploadExtractor`  |
| `okru.py`       | `OkRuExtractor`       |
| `filemoon.py`   | `FileMoonExtractor`   |
| `streamtape.py` | `StreamtapeExtractor` |
| `universal.py`  | `UniversalExtractor`  |

---

## 2. Interfaz pública obligatoria

Todo extractor expone **exactamente** estos dos métodos:

```python
def soporta(self, url: str) -> bool: ...
def extraer(self, url: str) -> str | None: ...
```

### `soporta(url)`

- Devuelve `True` si el extractor puede manejar esa URL.
- Comprueba dominio o patrón característico.
- **No** hace peticiones HTTP.
- Simple y rápido:

```python
def soporta(self, url):
    return "mp4upload.com" in url
```

`UniversalExtractor` es la excepción: siempre devuelve `True` porque actúa
como fallback. Va siempre **al final** del registro de extractores.

### `extraer(url)`

- Único punto de entrada para obtener el enlace del video.
- Devuelve el link (`str`) o **lanza excepción** si falla.
- No imprime nada. No llama a `sys.exit`. No usa `print`.
- No expone pasos intermedios. Si internamente necesitas varios pasos
  (descargar + parsear), se encapsulan dentro.

```python
def extraer(self, url):
    url_procesada = self._procesar_url(url)
    contenido = self._obtener_contenido(url_procesada)
    video = self._extraer_video_src(contenido)
    if not video:
        raise Exception("No se encontró el origen del video")
    return video
```

---

## 3. Constructor

```python
def __init__(self, session=None, debug=False):
    self.session = session or HTMLSession()
    self.debug = debug
```

- `session` inyectable para tests.
- `debug` booleano que controla el logging.
- Otros parámetros opcionales siempre con default.

---

## 4. Logging

Todo mensaje pasa por `_log()`:

```python
def _log(self, msg, level="info"):
    if not self.debug:
        return
    icons = {"info": "·", "ok": "✔", "fail": "✘", "warn": "⚠", "step": "→"}
    print(f"[<nombre>] {icons.get(level, '·')} {msg}", file=sys.stderr)
```

Reglas:

- **Sin `--debug`: silencio total.** Solo se imprime el resultado si hay éxito.
- **Con `--debug`: todo a `stderr`**, nunca a `stdout`.
- Niveles: `info`, `ok`, `warn`, `fail`, `step`.
- Prefijo `[<nombre>]` para identificar el extractor.

**Nunca** `print(...)` directo fuera de `_log`. Si el código imprime un error
sin `--debug`, es un bug.

---

## 5. Manejo de errores

- `extraer()` **lanza excepción** cuando falla.
- Los métodos auxiliares también lanzan.
- `extraer_y_mostrar()` (opcional, para uso standalone) captura y **solo con
  `--debug`** imprime el error:

```python
def extraer_y_mostrar(self, url):
    try:
        video_link = self.extraer(url)
        print(video_link)
        return video_link
    except Exception as e:
        if self.debug:
            print(f"[<nombre>] error: {e}", file=sys.stderr)
        sys.exit(1)
```

- Exit code `0` si encontró, `1` si falló.

---

## 6. Headers

**Nunca** generar headers al importar el módulo:

```python
# ❌ MAL
random_headers = real_headers()

class MiExtractor:
    def _obtener_contenido(self, url):
        headers = random_headers   # siempre los mismos
```

Correcto:

```python
# ✅ BIEN
from real_headers import real_headers

class MiExtractor:
    def _obtener_contenido(self, url):
        response = self.session.get(url, headers=real_headers())
```

Cada petición sale con User-Agent distinto → menos bloqueos.

Si necesitas headers extra:

```python
def _build_headers(self):
    headers = {
        "Referer": "https://ok.ru/",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    extra = real_headers()
    if isinstance(extra, dict):
        headers.update({k: v for k, v in extra.items() if k not in headers})
    return headers
```

---

## 7. Métodos auxiliares

Todos los métodos internos van con prefijo `_`:

```python
def _obtener_contenido(self, url): ...
def _extraer_video_src(self, contenido): ...
def _limpiar_temp(self): ...
```

- **Público** solo lo que el usuario del extractor necesita: `soporta`, `extraer`.
- Todo lo demás `_`.

---

## 8. Patrones de extracción

| Sitio                | Técnica                                                      |
| -------------------- | ------------------------------------------------------------ |
| FileMoon / SfastWish | `eval(function(p,a,c,k,e,d)` → ejecutar con `eval-unpacker`  |
| Voé                  | JSON ofuscado con ROT13 + base64 anidado                     |
| Streamtape           | `document.getElementById('captchalink'\|'botlink')` + concatenación |
| MP4Upload            | `src: "..."` en JS, o `.mp4` directo                         |
| OK.ru                | `data-module="OKVideo"` con `data-options` (JSON escapado)   |
| Universal            | Prueba todos los anteriores en orden                         |

Documenta la técnica en el docstring del módulo nuevo.

### Validación del link

Antes de devolver un link, valida que sea de video:

```python
def _es_link_valido(self, link):
    if not link or not re.match(r'https?://', link):
        return False
    if re.search(r'\.(png|jpg|jpeg|gif|svg|ico|css|js|woff2?)(\?|$)', link, re.I):
        return False
    return bool(re.search(r'\.(mp4|m3u8)(\?|$)', link, re.I))
```

Evita capturar `favicon.png`, `.css`, `.js` u otros recursos.

---

## 9. Detección de páginas de error

Algunos sitios devuelven `200 OK` con una página de error. Detectarlo:

```python
def _es_pagina_login(self, response):
    """MP4Upload redirige a /login cuando el video no existe."""
    if "/login" in response.url:
        return True
    if 'action="/login"' in response.text:
        return True
    return False
```

Si lo detectas, lanza excepción antes de parsear.

---

## 10. Estructura completa

```python
#!/usr/bin/env python3
# Extractor para <sitio> by IamJony

import sys
import re
from requests_html import HTMLSession
from real_headers import real_headers


class <Nombre>Extractor:
    def __init__(self, session=None, debug=False):
        self.session = session or HTMLSession()
        self.debug = debug

    # --- API pública ---
    def soporta(self, url): ...
    def extraer(self, url): ...
    def extraer_y_mostrar(self, url): ...

    # --- Logging ---
    def _log(self, msg, level="info"): ...

    # --- HTTP ---
    def _obtener_contenido(self, url): ...

    # --- Parsing ---
    def _extraer_video_src(self, contenido): ...


def _main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    debug = '--debug' in sys.argv or '-d' in sys.argv

    if not args:
        if debug:
            print("Error: URL no proporcionada", file=sys.stderr)
            print(f"Uso: {sys.argv[0]} [--debug] <URL>", file=sys.stderr)
        sys.exit(1)

    extractor = <Nombre>Extractor(debug=debug)
    extractor.extraer_y_mostrar(args[0])


if __name__ == "__main__":
    _main()
```

---

## 11. Registro en el paquete

En `src/streamvid/extractors/__init__.py`:

```python
from .<nombre> import <Nombre>Extractor

EXTRACTORS = [
    ...,
    <Nombre>Extractor,
    UniversalExtractor,   # siempre al final
]

__all__ = [
    ...,
    "<Nombre>Extractor",
]
```

En `src/streamvid/cli.py`, añadir a `EXTRACTOR_INFO`:

```python
'<nombre>': {
    'name': '<Nombre>',
    'class': <Nombre>Extractor,
    'example': 'https://...'
},
```

---

## 12. Checklist final

- [ ] Archivo en `extractors/<nombre>.py`, clase `<Nombre>Extractor`
- [ ] `soporta(url)` sin peticiones HTTP
- [ ] `extraer(url)` sin `print`, sin `sys.exit`, lanzando excepción al fallar
- [ ] Métodos internos con prefijo `_`
- [ ] `_log()` para todo mensaje, silenciado sin `debug`
- [ ] `real_headers()` llamado **por petición**, no al importar
- [ ] `_es_link_valido()` antes de devolver el link
- [ ] Registrado en `extractors/__init__.py` (`EXTRACTORS` y `__all__`)
- [ ] Registrado en `cli.py` (`EXTRACTOR_INFO` con `name`, `class`, `example`)
- [ ] Probado con URL válida: `streamvid "<url_válida>"`
- [ ] Probado con URL inválida (sin salida, exit 1): `streamvid "<url_inválida>"; echo $?`
- [ ] Probado con `--debug`: `streamvid --debug "<url_válida>"`

---

## 13. Errores frecuentes

| Error                                        | Causa                              | Solución                                       |
| -------------------------------------------- | ---------------------------------- | ---------------------------------------------- |
| `random_headers` al importar                 | Se generan una vez y se reutilizan | Llamar `real_headers()` en cada petición       |
| Captura `favicon.png`                        | Regex demasiado amplio             | Añadir `_es_link_valido()`                     |
| `print("Error: ...")` sin condicionar        | Se imprime siempre                 | Mover dentro de `if self.debug:`               |
| `sys.exit(1)` dentro de `extraer()`          | Mata el proceso del CLI            | Solo `extraer_y_mostrar` puede usar `sys.exit` |
| Métodos públicos que deberían ser privados   | Filtra la interfaz                 | Prefijo `_`                                    |
| `extraer()` devuelve `None` en vez de lanzar | El CLI no distingue el fallo       | Lanzar `Exception`                             |
| Detección de dominio duplicada en `cli.py`   | Se desincroniza                    | Usar `soporta()` del propio extractor          |
| `main()` en vez de `_main()`                 | Colisiona con `cli.main`           | Renombrar a `_main`                            |

---

## 14. Nota sobre URLs de prueba

Las URLs de estos sitios cambian o desaparecen. Antes de reportar un fallo
como bug del extractor:

1. Abre la URL en el navegador. Si da 404 → no es bug, el video ya no existe.
2. Verifica que el ID sea exacto (suelen ser aleatorios y sensibles al mínimo
   cambio).
3. Genera una URL nueva desde el propio sitio para probar.