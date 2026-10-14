# Guía de testing

Streamvid tiene **tres formas** de verificar que funciona. Cada una responde
a una pregunta distinta y se ejecuta en un momento distinto.

---

## Los tres tipos de test

| Comando                        | Qué prueba                         | Toca red | Cuándo usarlo                    |
| ------------------------------ | ---------------------------------- | -------- | -------------------------------- |
| `streamvid --test`             | Que el paquete está bien instalado | ❌        | Tras instalar o añadir extractor |
| `python scripts/smoke_test.py` | Que los sitios siguen vivos        | ✅        | Cuando algo falla o a diario     |
| `streamvid <url>`              | Uso normal                         | ✅        | Siempre                          |

Cada capa te lleva a un punto distinto del diagnóstico:

```
streamvid --test              → ¿mi paquete está bien?
        ↓ (si pasa)
smoke_test.py                 → ¿los sitios responden?
        ↓ (si pasa)
streamvid <url>               → uso real
```

---

## 1. Autotest offline: `streamvid --test`

Comprueba que el paquete está correctamente instalado. **No toca la red.**

### Qué verifica

- El paquete `streamvid` se importa sin errores
- Todos los extractores están registrados en `EXTRACTOR_INFO`
- Cada clase se instancia sin excepción
- `python -m streamvid` funciona

### Cómo se ejecuta

```bash
streamvid --test
```

Salida esperada:

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

Exit code `0` si todo OK, `1` si algo falla.

### Cuándo usarlo

- Acabas de instalar el paquete con `pip install -e .`
- Añadiste un extractor nuevo y quieres comprobar que importa bien
- Actualizaste dependencias y sospechas que algo se rompió
- Estás en una máquina sin red

### Cuándo NO es suficiente

`--test` **no prueba URLs reales ni extracción**. Si pasa pero el extractor
real falla, necesitas el smoke test.

---

## 2. Smoke test: `scripts/smoke_test.py`

Prueba cada extractor contra una **URL real** y verifica que devuelve un enlace.

### Qué verifica

- Cada URL de `scripts/urls.json` responde por HTTP (status 200)
- Cada extractor devuelve un enlace válido
- Al menos uno de los extractores sigue funcionando

### Cómo se ejecuta

```bash
python scripts/smoke_test.py
```

Salida esperada:

```
PRUEBA DE EXTRACTORES

--- Estado HTTP ---
  mp4upload    OK
  streamtape   OK
  filemoon     OK
  voe          OK
  okru         OK
  universal    OK

--- Extracción ---
  mp4upload    LIVE
  streamtape   LIVE
  filemoon     LIVE
  voe          LIVE
  okru         LIVE
  universal    LIVE

RESUMEN: 6/6 extractores funcionando
```

Exit code `0` si todos LIVE, `1` si alguno DEAD.

### Estados posibles

| Estado  | Significado                                           |
| ------- | ----------------------------------------------------- |
| `LIVE`  | El extractor devolvió un enlace válido                |
| `VACIO` | Devolvió `None` sin lanzar excepción                  |
| `DEAD`  | Lanzó excepción (error de red, parseo, video borrado) |

### Cuándo usarlo

- Un usuario te dice que un extractor no funciona
- Antes de hacer un release
- Como check diario (con GitHub Actions)
- Después de añadir o modificar un extractor

### Cómo añadir URLs de prueba

Edita `scripts/urls.json`:

```json
{
  "mp4upload":  "https://www.mp4upload.com/embed-XXXXX.html",
  "streamtape": "https://streamtape.com/e/XXXXX",
  "filemoon":   "https://sfastwish.com/e/XXXXX",
  "voe":        "https://voe.sx/e/XXXXX",
  "okru":       "https://ok.ru/videoembed/XXXXX",
  "universal":  "https://luluvdo.com/e/XXXXX"
}
```

**Nota:** los sitios borran videos con frecuencia. Si un extractor sale DEAD,
primero abre la URL en el navegador. Si da 404, la URL está muerta, no el
extractor.

### Cómo añadir un extractor al smoke

1. Añade la URL a `scripts/urls.json` con la clave del extractor
2. Añade la clase al `EXTRACTOR_MAP` de `scripts/smoke_test.py`:

```python
from streamvid import NuevoExtractor

EXTRACTOR_MAP = {
    ...,
    "nuevo": NuevoExtractor,
}
```

---

## 3. Test manual desde terminal

Prueba rápida del CLI real, con una URL concreta. Útil mientras desarrollas.

### Con un extractor concreto

```bash
streamvid -e voe "https://voe.sx/e/abc123"
```

### Con autodetección

```bash
streamvid "https://voe.sx/e/abc123"
```

### Con logs detallados

```bash
streamvid --debug "https://voe.sx/e/abc123"
```

Los logs van a `stderr`, el enlace a `stdout`. Para ver solo el enlace:

```bash
streamvid --debug "$URL" 2>/dev/null
```

### Verificar exit code

```bash
streamvid "$URL"
echo "Exit: $?"     # 0 = OK, 1 = fallo
```

---

## Flujo de diagnóstico completo

Cuando algo falla, sigue este orden:

### 1. ¿Está instalado el paquete?

```bash
streamvid --test
```

- **Falla** → problema de instalación → `pip install -e .`
- **Pasa** → siguiente

### 2. ¿Qué extractores fallan hoy?

```bash
python scripts/smoke_test.py
```

- **6/6 LIVE** → el problema era puntual (URL muerta)
- **Alguno DEAD** → siguiente

### 3. Ver el detalle del que falla

```bash
streamvid --debug -e <extractor> "<url>"
```

Fíjate en el último mensaje antes de fallar:

| Último mensaje                          | Problema                        |
| --------------------------------------- | ------------------------------- |
| `error de descarga: 404`                | Video borrado o ID inválido     |
| `error de descarga: timeout`            | Red o bloqueo del sitio         |
| `no se encontró el script con eval`     | El sitio cambió su HTML         |
| `no se encontró ningún .m3u8`           | El sitio cambió o requiere auth |
| `No se encontró captchalink ni botlink` | Streamtape cambió su JS         |

### 4. Arreglar el extractor

Consulta `docs/extractores.md` para los criterios.

### 5. Verificar que ya funciona

```bash
streamvid --debug -e <extractor> "<url>"
python scripts/smoke_test.py
```

---

## Cómo añadir un test nuevo

### Añadir un extractor al smoke

1. Edita `scripts/urls.json` y añade la URL con la clave del extractor
2. Edita `scripts/smoke_test.py` y añade la clase a `EXTRACTOR_MAP`
3. Corre `python scripts/smoke_test.py` para verificar

### Añadir una nueva comprobación offline a `--test`

Edita `run_self_test()` en `src/streamvid/cli.py`:

```python
def run_self_test():
    print_info("Autotest offline de extractores...\n")
    fallos = 0

    for key, info in EXTRACTOR_INFO.items():
        cls = info['class']
        nombre = info['name']
        try:
            inst = cls(debug=False)

            # Comprobaciones adicionales
            assert hasattr(inst, "extraer"), f"{nombre} sin extraer()"
            assert hasattr(inst, "soporta"), f"{nombre} sin soporta()"

            print(f"  {color_text('✓', Colors.GREEN)} {nombre}")
        except Exception as e:
            print(f"  {color_text('✗', Colors.RED)} {nombre}: {e}")
            fallos += 1

    total = len(EXTRACTOR_INFO)
    print(f"\n{total - fallos}/{total} extractores válidos")
    return fallos == 0
```

---

## GitHub Actions (CI)

El smoke test se ejecuta automáticamente vía GitHub Actions. Ver
`.github/workflows/smoke.yml`.

Se dispara:

- **Cada día a las 03:00 UTC** (cron)
- **Manual** desde la pestaña Actions
- **En cada push a `main`**

### Ver resultados

1. Ve a tu repo en GitHub
2. Pestaña **Actions**
3. Clic en el workflow **Smoke test**
4. Clic en un run para ver los logs paso a paso

### Cómo lanzarlo manualmente

1. Actions → **Smoke test**
2. Botón **Run workflow** (arriba a la derecha)
3. Elige la rama `main`
4. **Run workflow**

En 30 segundos tendrás el resultado.

---

## Errores comunes

| Error                                              | Causa                                  | Solución                       |
| -------------------------------------------------- | -------------------------------------- | ------------------------------ |
| `ModuleNotFoundError: No module named 'streamvid'` | No instalado                           | `pip install -e .`             |
| `eval-unpacker no encontrado`                      | Falta la dependencia                   | `npm install -g eval-unpacker` |
| `404 Client Error`                                 | Video borrado o ID incorrecto          | Abrir URL en el navegador      |
| Todos los extractores `DEAD`                       | Sin conexión a internet                | Revisar red                    |
| Solo un extractor `DEAD`                           | El sitio cambió o el video fue borrado | Ver con `--debug`              |
| `captchalink` sin match                            | Streamtape cambió su JS                | Actualizar extractor           |

---

## Buenas prácticas

### Antes de commitear

```bash
streamvid --test
python scripts/smoke_test.py
```

Si los dos pasan, tu cambio no rompió nada importante.

### Antes de un release

1. `streamvid --test` — instalación OK
2. `python scripts/smoke_test.py` — todos LIVE
3. Actualizar `CHANGELOG.md`
4. Crear el tag

### Al añadir un extractor

1. Sigue `docs/extractores.md`
2. Añade la URL de prueba a `scripts/urls.json`
3. Añade la clase a `EXTRACTOR_MAP` en `smoke_test.py`
4. Corre `streamvid --test` y `python scripts/smoke_test.py`
5. Confirma `7/7 funcionando`

---

## Lo que NO se prueba

- **Tests unitarios** con `pytest` — no se han implementado
- **Cobertura de código** — no medida
- **Casos límite** con mocks — no cubiertos
