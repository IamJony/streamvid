#!/usr/bin/env python3
# Smoke test: prueba extractores con URLs reales. by IamJony
#
# Uso:
#   python scripts/smoke_test.py
#
# Exit code:
#   0 → todos LIVE con headers correctos
#   1 → algún fallo

import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from string import Template

import requests

from streamvid import (
    FileMoonExtractor,
    MP4UploadExtractor,
    OkRuExtractor,
    StreamtapeExtractor,
    UniversalExtractor,
    VoeExtractor,
)

EXTRACTOR_MAP = {
    "mp4upload":  MP4UploadExtractor,
    "streamtape": StreamtapeExtractor,
    "filemoon":   FileMoonExtractor,
    "voe":        VoeExtractor,
    "okru":       OkRuExtractor,
    "universal":  UniversalExtractor,
}

URLS_FILE = Path(__file__).parent / "urls.json"
BASE_DIR = Path(__file__).parent.parent
STATUS_FILE = BASE_DIR / "status.json"
HTML_FILE = BASE_DIR / "docs" / "status.html"


def _acepta_debug(cls):
    import inspect
    try:
        sig = inspect.signature(cls.__init__)
        return "debug" in sig.parameters
    except (ValueError, TypeError):
        return False


# ---------- Fase 1: HTTP ----------

def fase_http(urls):
    print("--- Estado HTTP ---")
    resultados = {}
    for nombre, url in urls.items():
        try:
            r = requests.get(url, timeout=10)
            status = "OK" if r.status_code == 200 else f"estado {r.status_code}"
            print(f"  {nombre:<12} {status}")
            resultados[nombre] = r.status_code
        except Exception as e:
            print(f"  {nombre:<12} error de conexión ({e})")
            resultados[nombre] = None
    return resultados


# ---------- Fase 2: extracción + headers ----------

def probar(nombre, cls, url):
    resultado = {
        "live": False,
        "url": None,
        "headers": None,
        "headers_antes": None,
        "error": None,
        "tested_url": url,
    }

    try:
        extractor = cls(debug=False) if _acepta_debug(cls) else cls()
    except Exception as e:
        resultado["error"] = f"init: {e}"
        return resultado

    if hasattr(extractor, "obtener_headers"):
        try:
            resultado["headers_antes"] = extractor.obtener_headers()
        except Exception as e:
            resultado["error"] = f"headers_antes: {e}"
            return resultado

    try:
        link = extractor.extraer(url)
    except Exception as e:
        resultado["error"] = str(e)
        return resultado

    if not link:
        resultado["error"] = "VACIO"
        return resultado

    resultado["live"] = True
    resultado["url"] = link

    if hasattr(extractor, "obtener_headers"):
        try:
            resultado["headers"] = extractor.obtener_headers()
        except Exception as e:
            resultado["error"] = f"headers_despues: {e}"

    return resultado


def fase_extraccion(urls):
    print("\n--- Extracción ---")
    resultados = {}

    for nombre, url in urls.items():
        cls = EXTRACTOR_MAP.get(nombre)
        if cls is None:
            print(f"  {nombre:<12} (sin extractor, saltando)")
            continue

        r = probar(nombre, cls, url)
        resultados[nombre] = r

        if r["live"]:
            print(f"  {nombre:<12} LIVE")
        elif r["error"] == "VACIO":
            print(f"  {nombre:<12} VACIO")
        else:
            print(f"  {nombre:<12} DEAD ({r['error']})")

    return resultados


# ---------- Fase 3: headers ----------

def fase_headers(resultados):
    print("\n--- Headers ---")
    ok = 0
    total = 0

    for nombre, r in resultados.items():
        if not r["live"]:
            print(f"  {nombre:<12} (saltando, no LIVE)")
            continue

        total += 1
        headers = r["headers"]

        if headers is None:
            print(f"  {nombre:<12} \033[91m✗\033[0m sin headers")
            continue

        if "Referer" not in headers:
            print(f"  {nombre:<12} \033[91m✗\033[0m sin Referer")
            continue

        if "User-Agent" not in headers:
            print(f"  {nombre:<12} \033[91m✗\033[0m sin User-Agent")
            continue

        ref = headers["Referer"]
        print(f"  {nombre:<12} \033[92m✓\033[0m Referer={ref}")
        ok += 1

    return ok, total


# ---------- Fase 4: API ----------

def fase_api(resultados):
    print("\n--- API: obtener_headers antes/después ---")

    comprobados = 0
    for nombre, r in resultados.items():
        if not r["live"]:
            continue

        antes = r.get("headers_antes")
        despues = r.get("headers")

        if antes is not None:
            print(f"  {nombre:<12} \033[91m✗\033[0m antes de extraer ya había headers")
            return False

        if despues is None:
            print(f"  {nombre:<12} \033[91m✗\033[0m después de extraer no hay headers")
            return False

        print(f"  {nombre:<12} \033[92m✓\033[0m None antes, dict después")
        comprobados += 1

    return comprobados > 0


# ---------- Guardar status.json ----------

def guardar_status(resultados, headers_ok, headers_total, http_status):
    total = len(resultados)
    live = sum(1 for r in resultados.values() if r["live"])

    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": total,
        "live": live,
        "headers_ok": headers_ok,
        "headers_total": headers_total,
        "http_status": http_status,
        "extractores": {
            nombre: {
                "live": r["live"],
                "info": r["url"] or "",
                "headers": r["headers"],
                "error": r["error"],
                "tested_url": r["tested_url"],
            }
            for nombre, r in resultados.items()
        },
    }
    STATUS_FILE.write_text(
        json.dumps(status, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nstatus.json escrito en {STATUS_FILE}")
    return status


# ---------- Guardar HTML ----------

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>streamvid :: status</title>
<style>
  :root {
    --bg: #0a0e0a;
    --bg-panel: #0d140d;
    --green: #00ff88;
    --green-dim: #00cc6a;
    --green-glow: #00ff8855;
    --red: #ff3366;
    --yellow: #ffcc00;
    --gray: #5a6b5a;
    --border: #1a281a;
    --text: #b8c8b8;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: ui-monospace, "SF Mono", "Cascadia Code", Consolas, monospace;
    background: var(--bg);
    color: var(--text);
    padding: 2rem 1rem;
    min-height: 100vh;
    background-image:
      radial-gradient(circle at 50% 0%, #00ff8808 0%, transparent 60%),
      repeating-linear-gradient(0deg, transparent, transparent 2px, #00ff8803 2px, #00ff8803 4px);
    font-size: 14px;
    line-height: 1.5;
  }
  .wrap { max-width: 1000px; margin: 0 auto; }

  header {
    border: 1px solid var(--border);
    background: var(--bg-panel);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    border-radius: 4px;
    box-shadow: 0 0 24px var(--green-glow), inset 0 0 24px #00ff8805;
  }
  .banner {
    color: var(--green);
    font-size: 1.1rem;
    letter-spacing: 2px;
    text-shadow: 0 0 8px var(--green-glow);
    margin-bottom: 0.75rem;
  }
  .banner::before { content: "$$ "; color: var(--green-dim); }
  .banner::after {
    content: "_";
    animation: blink 1s steps(1) infinite;
    margin-left: 2px;
  }
  @keyframes blink { 50% { opacity: 0; } }

  .summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
  }
  .stat {
    border: 1px solid var(--border);
    background: #050905;
    padding: 0.75rem;
    border-radius: 3px;
  }
  .stat .k { color: var(--gray); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
  .stat .v {
    color: var(--green);
    font-size: 1.25rem;
    margin-top: 0.25rem;
    text-shadow: 0 0 6px var(--green-glow);
  }
  .stat.bad .v { color: var(--red); text-shadow: 0 0 6px #ff336655; }
  .stat.warn .v { color: var(--yellow); text-shadow: 0 0 6px #ffcc0055; }

  table {
    width: 100%;
    border-collapse: collapse;
    border: 1px solid var(--border);
    background: var(--bg-panel);
    border-radius: 4px;
    overflow: hidden;
  }
  thead { background: #050905; }
  th {
    text-align: left;
    padding: 0.75rem 1rem;
    font-size: 0.75rem;
    letter-spacing: 1.5px;
    color: var(--green);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border);
  }
  td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover { background: #0d140d66; }

  .name { color: var(--green); font-weight: bold; }
  .live { color: var(--green); text-shadow: 0 0 6px var(--green-glow); font-weight: bold; }
  .dead { color: var(--red); text-shadow: 0 0 6px #ff336655; font-weight: bold; }

  .url {
    color: var(--gray);
    font-size: 0.8rem;
    word-break: break-all;
    max-width: 380px;
    display: inline-block;
  }
  .url a { color: var(--green-dim); text-decoration: none; }
  .url a:hover { color: var(--green); text-decoration: underline; }

  .headers {
    font-size: 0.75rem;
    color: var(--gray);
    margin-top: 0.25rem;
  }
  .headers code {
    color: var(--green-dim);
    background: #050905;
    padding: 1px 4px;
    border-radius: 2px;
  }

  .tested {
    color: var(--gray);
    font-size: 0.7rem;
    word-break: break-all;
    max-width: 300px;
    display: inline-block;
  }

  footer {
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    color: var(--gray);
    font-size: 0.75rem;
    text-align: center;
  }
  footer a { color: var(--green-dim); text-decoration: none; }
  footer a:hover { color: var(--green); }
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="banner">streamvid --status</div>
  <div style="color:var(--gray); font-size:0.8rem;">
    video extractor · $live/$total extractores live · actualizado $timestamp
  </div>
  <div class="summary">
    <div class="stat $cls_live">
      <div class="k">extractores</div>
      <div class="v">$live/$total</div>
    </div>
    <div class="stat $cls_headers">
      <div class="k">headers ok</div>
      <div class="v">$headers_ok/$headers_total</div>
    </div>
    <div class="stat $cls_global">
      <div class="k">estado global</div>
      <div class="v">$global_status</div>
    </div>
    <div class="stat">
      <div class="k">última prueba</div>
      <div class="v" style="font-size:0.9rem;">$timestamp</div>
    </div>
  </div>
</header>

<table>
<thead>
  <tr>
    <th>Extractor</th>
    <th>Estado</th>
    <th>URL probada</th>
    <th>Link extraído / Headers</th>
  </tr>
</thead>
<tbody>
$rows
</tbody>
</table>

<footer>
  Estado de extractores by IamJony, se actualiza a diario. 
  · <a href="../actions">github actions</a>
  · <a href="status.json">json crudo</a>
</footer>

</div>
</body>
</html>
""")


def _fila_html(nombre, r):
    if r["live"]:
        estado = '<span class="live">● LIVE</span>'
    elif r["error"] == "VACIO":
        estado = '<span class="dead">○ EMPTY</span>'
    else:
        estado = '<span class="dead">● DEAD</span>'

    tested = html.escape(r.get("tested_url") or "-")
    tested_short = tested if len(tested) < 60 else tested[:57] + "..."

    if r["live"] and r["url"]:
        link = html.escape(r["url"])
        link_short = link if len(link) < 80 else link[:77] + "..."
        urls_html = f'<a href="{link}" target="_blank" rel="noopener">{link_short}</a>'
    elif r["error"]:
        urls_html = f'<span class="dead">{html.escape(r["error"][:80])}</span>'
    else:
        urls_html = '<span class="url">—</span>'

    headers_html = ""
    if r["headers"]:
        ref = html.escape(r["headers"].get("Referer", "-"))
        ua = html.escape(r["headers"].get("User-Agent", "-"))[:50]
        headers_html = (
            f'<div class="headers">'
            f'<code>Referer:</code> {ref}<br>'
            f'<code>UA:</code> {ua}...'
            f'</div>'
        )

    return (
        f'<tr>'
        f'<td class="name">{nombre}</td>'
        f'<td>{estado}</td>'
        f'<td><span class="tested">{tested_short}</span></td>'
        f'<td><div class="url">{urls_html}</div>{headers_html}</td>'
        f'</tr>'
    )


def guardar_html(status, resultados, headers_ok, headers_total):
    total = status["total"]
    live = status["live"]
    ts = status["timestamp"]

    cls_live = "bad" if live < total else ""
    cls_headers = "warn" if headers_ok < headers_total else ""
    cls_global = "bad" if live < total else ""

    if live == total and headers_ok == headers_total:
        global_status = "ALL GREEN"
    elif live == total:
        global_status = "LIVE"
    elif live >= total / 2:
        global_status = "DEGRADED"
    else:
        global_status = "DOWN"

    rows = "\n".join(_fila_html(n, r) for n, r in resultados.items())

    html_out = HTML_TEMPLATE.substitute(
        live=live,
        total=total,
        headers_ok=headers_ok,
        headers_total=headers_total,
        timestamp=ts,
        cls_live=cls_live,
        cls_headers=cls_headers,
        cls_global=cls_global,
        global_status=global_status,
        rows=rows,
    )

    HTML_FILE.parent.mkdir(exist_ok=True)
    HTML_FILE.write_text(html_out, encoding="utf-8")
    print(f"HTML escrito en {HTML_FILE}")


# ---------- main ----------

def main():
    print("PRUEBA DE EXTRACTORES\n")

    urls = json.loads(URLS_FILE.read_text(encoding="utf-8"))

    http_status = fase_http(urls)
    resultados = fase_extraccion(urls)
    headers_ok, headers_total = fase_headers(resultados)
    api_ok = fase_api(resultados)

    status = guardar_status(resultados, headers_ok, headers_total, http_status)
    guardar_html(status, resultados, headers_ok, headers_total)

    total = len(resultados)
    live = sum(1 for r in resultados.values() if r["live"])

    print(f"\n--- RESUMEN ---")
    print(f"  Extracción: {live}/{total} extractores LIVE")
    print(f"  Headers:    {headers_ok}/{headers_total} con Referer + User-Agent")
    print(f"  API:        {'OK' if api_ok else 'FALLO'}")

    todo_ok = (live == total) and (headers_ok == headers_total) and api_ok
    return 0 if todo_ok else 1


if __name__ == "__main__":
    sys.exit(main())
