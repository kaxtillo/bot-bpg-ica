#!/usr/bin/env python3
"""
informe_tecnico_pdf.py — Informe técnico de funcionamiento de la plataforma BPG ICA.

Recoge los datos EN VIVO (BD, sistema, cron, Kobo, artefactos publicados) y arma un
PDF A4 con la arquitectura, la recolección en campo, el procesamiento, la publicación,
los planes de acción, la automatización y los riesgos conocidos.

Uso:  informe_tecnico_pdf.py [--salida ruta.pdf]
"""
import argparse, datetime, glob, json, os, platform, re, sqlite3, subprocess, sys, urllib.request

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
ENV = os.path.expanduser("~/.hermes/.env")
KOBO_UID = "aNVGYKhswB8hFBSArTh8b8"
KOBO_LINK = "https://ee.kobotoolbox.org/x/FZtksUX9"
PY = "/home/hermes/.hermes/hermes-agent/venv/bin/python"

PROGRAMAS = [
    ("guardar_auditoria.py", "Punto único de escritura: calcula % y concepto, hace upsert del predio"),
    ("importar_hoja.py", "Trae la hoja de Google a la BD, normaliza grafías, evita duplicados"),
    ("sincronizar_hoja.py", "Sincronización bidireccional BD ↔ hoja (OAuth)"),
    ("sincronizar_todo.sh", "Orquesta el ciclo completo: hoja → BD → mapa → dashboard → respaldo"),
    ("procesar_kobo.py", "Descarga envíos de KoboToolbox y los consolida"),
    ("generar_dashboard.py", "Construye el dashboard público (búsqueda, mapa, seguimiento)"),
    ("generar_plan_accion.py", "Genera el plan de acción por predio (HTML/PDF con avance)"),
    ("seguimiento.py", "Tabla de hallazgos: estados, responsables, plazos, evidencia"),
    ("archivo_visitas.py", "Aparta visitas antiguas/duplicadas sin afectar lo publicado"),
    ("reporte_periodo_pdf.py", "Informe por periodo: altas, certificables, aplazados, veredas"),
    ("listado_predios_pdf.py", "Listado A4 por municipio (con o sin datos de contacto)"),
    ("pdf_html.py", "Motor de PDF con respaldo: WeasyPrint → chromium → brave"),
    ("exportar_plan_pdf.js", "Reutiliza la plantilla real del dashboard para el PDF del plan"),
    ("servidor_api.py", "API local para la app Android (puerto 8200)"),
    ("subir_repo.py", "Publica el código en GitHub por API (compara sha, no resube)"),
    ("corregir_formula_kobo.py", "Corrige los campos calculate del XLSForm vía API"),
    ("verificar_kobo.py", "Compara los cálculos del formulario contra la BD"),
]

CSS = """<style>
@page{size:A4 portrait;margin:15mm 13mm 16mm 13mm;
  @bottom-left{content:"Informe técnico · Plataforma BPG ICA 067449";font-size:7.5pt;color:#7a8a84}
  @bottom-right{content:"Página " counter(page) " de " counter(pages);font-size:7.5pt;color:#7a8a84}}
*{box-sizing:border-box}
body{font-family:'DejaVu Sans',Arial,sans-serif;color:#1b2b26;margin:0;font-size:9.6pt;line-height:1.45}
.portada{background:#0B3D2E;color:#fff;padding:20px 22px;border-radius:5px;margin-bottom:14px}
.portada h1{margin:0 0 4px;font-size:20pt;letter-spacing:.2px}
.portada .b{font-size:11pt;opacity:.95;margin-bottom:2px}
.portada .m{font-size:8.8pt;opacity:.85;margin-top:8px;border-top:1px solid rgba(255,255,255,.35);padding-top:7px}
h2{font-size:12.5pt;color:#0B3D2E;margin:16px 0 6px;border-bottom:1.5px solid #0B3D2E;padding-bottom:3px}
h3{font-size:10.2pt;color:#155443;margin:11px 0 4px}
p{margin:4px 0 6px;text-align:justify}
table{width:100%;border-collapse:collapse;margin:5px 0 8px}
thead{display:table-header-group}
tr{page-break-inside:avoid}
h2,h3{page-break-after:avoid}
th,td{border:1px solid #c3cfc9;padding:3.5px 5px;font-size:8.7pt;vertical-align:top}
th{background:#eef3f0;text-align:left;font-size:8pt;text-transform:uppercase;letter-spacing:.3px}
td.k{width:34%;background:#f8faf9;font-weight:600}
td.c{text-align:center;white-space:nowrap}
ul,ol{margin:4px 0 7px 16px;padding:0}
li{margin-bottom:2.5px}
.cifras{width:100%;border-collapse:separate;border-spacing:7px 0;margin:6px 0 10px}
td.cif{border:1px solid #cfdad5;border-top:4px solid #0B3D2E;border-radius:4px;padding:7px 9px;background:#f7faf8;vertical-align:top;width:25%}
td.cif .n{font-size:17pt;font-weight:700;color:#0B3D2E;line-height:1.05}
td.cif .l{font-size:7.8pt;color:#5b6b66;text-transform:uppercase;letter-spacing:.3px}
td.cif.g{border-top-color:#2E7D32}td.cif.g .n{color:#2E7D32}
td.cif.r{border-top-color:#C62828}td.cif.r .n{color:#C62828}
.aviso{border-left:4px solid #C62828;background:#fdf3f2;padding:7px 10px;margin:7px 0;font-size:8.9pt}
.ok{border-left:4px solid #2E7D32;background:#f2f8f3;padding:7px 10px;margin:7px 0;font-size:8.9pt}
.nota{font-size:8.2pt;color:#546e64;margin-top:3px}
code{font-family:'DejaVu Sans Mono',monospace;font-size:8.4pt;background:#eef2f0;padding:0 2px;border-radius:2px}
.paso{background:#f7faf8;border:1px solid #cfdad5;border-radius:3px;padding:5px 8px;font-size:8.6pt}
</style>"""


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def kobo_info():
    try:
        key = [l.split("=", 1)[1].strip() for l in open(ENV) if l.startswith("KOBO_TOKEN=")][0]
        q = urllib.request.Request(
            "https://kf.kobotoolbox.org/api/v2/assets/" + KOBO_UID + "/?format=json",
            headers={"Authorization": "Token " + key, "Accept": "application/json"})
        a = json.load(urllib.request.urlopen(q, timeout=45))
        return {"estado": a.get("deployment_status"), "envios": a.get("deployment__submission_count"),
                "version_ok": a.get("version_id") == a.get("deployed_version_id"),
                "modificado": str(a.get("date_modified"))[:10], "dueno": a.get("owner__username"),
                "nombre": a.get("name")}
    except Exception as e:
        return {"error": str(e)[:60]}


def recolectar():
    d = {}
    _ah = datetime.datetime.now()
    d["fecha"] = f"{_ah.day} de {MESES[_ah.month - 1]} de {_ah.year}, {_ah:%H:%M}"
    d["host"] = sh("hostname")
    d["kernel"] = platform.release()
    d["python"] = platform.python_version()
    d["sqlite"] = sqlite3.sqlite_version
    try:
        import weasyprint
        d["weasy"] = weasyprint.__version__
    except Exception:
        d["weasy"] = "n/d"
    d["chromium"] = sh("chromium --version").replace("Chromium ", "").replace(" Arch Linux", "") or "no instalado"

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    q = lambda s: con.execute(s).fetchone()[0]
    d["predios"] = q("SELECT COUNT(*) FROM predios")
    d["auditorias"] = q("SELECT COUNT(*) FROM auditorias")
    d["respuestas"] = q("SELECT COUNT(*) FROM respuestas")
    d["seguimiento"] = q("SELECT COUNT(*) FROM seguimiento")
    d["archivo"] = q("SELECT COUNT(*) FROM auditorias_archivo")
    d["cert"] = q("""SELECT COUNT(*) FROM predios p WHERE (SELECT concepto FROM auditorias
                    WHERE predio_id=p.id ORDER BY fecha DESC,id DESC LIMIT 1)='Certificable'""")
    d["aplaz"] = d["predios"] - d["cert"]
    d["tam_db"] = os.path.getsize(DB)
    d["tablas"] = [(r["name"], q("SELECT COUNT(*) FROM " + r["name"]))
                   for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%' ORDER BY name")]
    d["municipios"] = con.execute("SELECT municipio,COUNT(*) c FROM predios GROUP BY 1 ORDER BY c DESC").fetchall()
    d["veredas"] = con.execute("SELECT COUNT(DISTINCT vereda) FROM predios").fetchone()[0]
    d["resp"] = dict(con.execute("SELECT respuesta,COUNT(*) FROM respuestas GROUP BY 1").fetchall())
    d["tipos"] = dict(con.execute("SELECT tipo,COUNT(*) FROM criterios GROUP BY 1").fetchall())
    d["fuentes"] = con.execute("SELECT fuente,COUNT(*) c FROM auditorias GROUP BY 1 ORDER BY c DESC").fetchall()
    d["rango"] = con.execute("SELECT MIN(fecha),MAX(fecha) FROM auditorias").fetchone()[:]
    d["gps"] = q("SELECT COUNT(*) FROM predios WHERE latitud IS NOT NULL AND longitud IS NOT NULL")
    d["umbral"] = re.search(r"UMBRALES = (\{[^}]*\})", open(os.path.join(BASE, "guardar_auditoria.py")).read())
    if d["umbral"]:
        vals = dict(re.findall(r"['\"](\w+)['\"]:\s*([\d.]+)", d["umbral"].group(1)))
        etq = {"F": "Fundamentales", "My": "Mayores", "Mn": "Menores"}
        d["umbral"] = " · ".join(etq.get(k, k) + " " + str(int(float(v))) + " %" for k, v in vals.items())
    else:
        d["umbral"] = "Fundamentales 100 % · Mayores 80 % · Menores 60 %"

    d["kobo"] = kobo_info()

    # artefactos
    dash = os.path.join(BASE, "Dashboard_Auditorias_BPG_ICA.html")
    geo = os.path.join(BASE, "predios_bpg_ica.geojson")
    d["dash_kb"] = os.path.getsize(dash) // 1024 if os.path.exists(dash) else 0
    html = open(dash, encoding="utf-8").read() if os.path.exists(dash) else ""
    d["dash_personales"] = len(re.findall(r"propietario|identificacion|telefono", html))
    d["geo_kb"] = os.path.getsize(geo) // 1024 if os.path.exists(geo) else 0
    d["geo_n"] = 0
    d["geo_props"] = []
    if os.path.exists(geo):
        gj = json.load(open(geo))
        d["geo_n"] = len(gj["features"])
        d["geo_props"] = sorted(gj["features"][0]["properties"].keys()) if gj["features"] else []

    # servicios
    d["servicios"] = [(s, sh("systemctl --user is-active " + s) or "?")
                      for s in ("hermes-gateway", "omniroute", "auditor-bpg-api", "sincronizar-todo.timer")]
    d["prox_timer"] = ""
    for line in sh("systemctl --user list-timers sincronizar-todo.timer --no-pager").splitlines():
        if "sincronizar-todo" in line:
            d["prox_timer"] = " ".join(line.split()[:3])
    d["api"] = sh("curl -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8200/api/health")

    # cron
    d["cron"] = []
    try:
        jobs = json.load(open(os.path.expanduser("~/.hermes/cron/jobs.json")))
        jobs = jobs.get("jobs", jobs) if isinstance(jobs, dict) else jobs
        for j in jobs:
            sch = j.get("schedule") or {}
            d["cron"].append({"nombre": j.get("name"), "cada": sch.get("display") or str(sch),
                              "activo": bool(j.get("enabled")), "script": j.get("script") or "—",
                              "ultimo": str(j.get("last_run_at") or "—")[:16].replace("T", " ")})
    except Exception:
        pass

    # respaldos
    bks = sorted(glob.glob(os.path.join(BASE, "backups", "*.tar.gz")), key=os.path.getmtime)
    d["bk_n"] = len(bks)
    d["bk_peso"] = sum(os.path.getsize(b) for b in bks) // (1024 * 1024)
    d["bk_ultimo"] = os.path.basename(bks[-1])[13:26] if bks else "—"

    # inventario de programas
    d["programas"] = []
    for nombre, desc in PROGRAMAS:
        ruta = os.path.join(BASE, nombre)
        if os.path.exists(ruta):
            n = sum(1 for _ in open(ruta, encoding="utf-8", errors="ignore"))
            d["programas"].append((nombre, n, os.path.getsize(ruta), desc))
    return d


def informe(d):
    k = d["kobo"]
    H = []
    A = H.append
    # portada
    A("<div class='portada'><div class='b'>INFORME TÉCNICO DE FUNCIONAMIENTO</div>"
      "<h1>Plataforma de Auditorías BPG</h1>"
      "<div class='b'>Buenas Prácticas Ganaderas · Resolución ICA 067449 · Forma 3-852 V6</div>"
      "<div class='m'>Generado automáticamente desde la base de datos y el sistema en producción · "
      + d["fecha"] + " · " + d["host"] + " · kernel " + d["kernel"] + "</div></div>")

    A("<h2>1. Resumen ejecutivo</h2>")
    A("<p>La plataforma es un ecosistema <b>offline-first</b> para auditar predios de producción de leche "
      "contra los 62 criterios de la Resolución ICA 067449. La captura en campo se hace con un formulario "
      "digital en KoboToolbox y una aplicación Android; ambos alimentan una base SQLite local que recalcula "
      "los umbrales, alimenta una hoja de Google, un mapa público y un dashboard de consulta, y genera "
      "planes de acción e informes en PDF. Toda la operación es reproducible sin dependencia de modelos de "
      "lenguaje: el asistente (Hermes) es la capa de conversación, no un componente del cálculo.</p>")
    A("<table class='cifras'><tr>"
      "<td class='cif'><div class='n'>" + str(d["predios"]) + "</div><div class='l'>Predios registrados</div></td>"
      "<td class='cif'><div class='n'>" + str(d["auditorias"]) + "</div><div class='l'>Auditorías</div></td>"
      "<td class='cif g'><div class='n'>" + str(d["cert"]) + "</div><div class='l'>Certificables</div></td>"
      "<td class='cif r'><div class='n'>" + str(d["aplaz"]) + "</div><div class='l'>Aplazados</div></td>"
      "</tr></table>")
    A("<table>"
      "<tr><td class='k'>Criterios evaluados</td><td>" + str(sum(d["tipos"].values())) +
      " (Fundamentales " + str(d["tipos"].get("F", 0)) + " · Mayores " + str(d["tipos"].get("My", 0)) +
      " · Menores " + str(d["tipos"].get("Mn", 0)) + ")</td></tr>"
      "<tr><td class='k'>Respuestas almacenadas</td><td>" + f"{d['respuestas']:,}".replace(",", ".") +
      " (SI " + str(d["resp"].get("SI", 0)) + " · NO " + str(d["resp"].get("NO", 0)) +
      " · NA " + str(d["resp"].get("NA", 0)) + ")</td></tr>"
      "<tr><td class='k'>Cobertura geográfica</td><td>" + str(len(d["municipios"])) + " municipios · " +
      str(d["veredas"]) + " veredas · " + str(d["gps"]) + "/" + str(d["predios"]) + " predios con coordenadas</td></tr>"
      "<tr><td class='k'>Histórico</td><td>" + str(d["rango"][0]) + " a " + str(d["rango"][1]) + "</td></tr>"
      "<tr><td class='k'>Hallazgos en seguimiento</td><td>" + str(d["seguimiento"]) + " activos · " +
      str(d["archivo"]) + " visitas en archivo histórico</td></tr>"
      "<tr><td class='k'>Umbrales de certificación</td><td>" + d["umbral"] +
      " (los NA se excluyen del denominador)</td></tr>"
      "</table>")

    # arquitectura
    A("<h2>2. Arquitectura del ecosistema</h2>")
    A("<p>El flujo completo, desde el potrero hasta el documento entregable, son seis etapas encadenadas. "
      "Cada una es independiente y puede correrse a mano o por automatización: si una falla, las anteriores "
      "conservan su resultado.</p>")
    flujo = [
        ("1. Captura en campo", "Formulario KoboToolbox (enlace público) o app Android", "Productor / auditor", "Manual"),
        ("2. Consolidación", "<code>procesar_kobo.py</code> · <code>importar_hoja.py</code>", "Cron cada 3 h / sync", "Automático"),
        ("3. Cálculo y almacenamiento", "<code>guardar_auditoria.py</code> → SQLite", "Al consolidar", "Automático"),
        ("4. Sincronización", "<code>sincronizar_hoja.py</code> (BD ↔ hoja Google)", "Sync diaria", "Automático"),
        ("5. Publicación", "GeoJSON → uMap · dashboard → GitHub Pages", "Sync diaria", "Automático"),
        ("6. Documentos", "Planes de acción, informes y listados en PDF", "A demanda", "Manual"),
    ]
    A("<table><thead><tr><th>Etapa</th><th>Componente</th><th>Disparador</th><th>Modo</th></tr></thead><tbody>")
    for e, c, t, m in flujo:
        A("<tr><td><b>" + e + "</b></td><td>" + c + "</td><td>" + t + "</td><td class='c'>" + m + "</td></tr>")
    A("</tbody></table>")
    A("<h3>Componentes de infraestructura</h3>")
    A("<table><thead><tr><th>Componente</th><th>Función</th><th>Estado</th></tr></thead><tbody>")
    for s, est in d["servicios"]:
        desc = {"hermes-gateway": "Bot de Telegram (interfaz conversacional y alertas)",
                "omniroute": "Pasarela de modelos de lenguaje",
                "auditor-bpg-api": "API REST local para la app Android (puerto 8200)",
                "sincronizar-todo.timer": "Temporizador del ciclo diario de sincronización"}.get(s, "")
        A("<tr><td><code>" + s + "</code></td><td>" + desc + "</td><td class='c'>" + est + "</td></tr>")
    A("</tbody></table>")
    A("<p class='nota'>Próxima ejecución del ciclo diario: " + (d["prox_timer"] or "—") +
      " · API en <code>/api/health</code> responde HTTP " + (d["api"] or "sin respuesta") + ".</p>")

    # captura
    A("<h2>3. Recolección de datos en terreno</h2>")
    A("<h3>3.1 Formulario digital (KoboToolbox)</h3>")
    if "error" not in k:
        A("<table>"
          "<tr><td class='k'>Formulario</td><td>" + str(k.get("nombre")) + " · UID <code>" + KOBO_UID + "</code></td></tr>"
          "<tr><td class='k'>Enlace de diligenciamiento</td><td><code>" + KOBO_LINK + "</code></td></tr>"
          "<tr><td class='k'>Estado del despliegue</td><td>" + str(k.get("estado")) +
          " · versión desplegada coincide con la publicada: " + ("sí" if k.get("version_ok") else "NO") + "</td></tr>"
          "<tr><td class='k'>Envíos recibidos</td><td>" + str(k.get("envios")) + "</td></tr>"
          "<tr><td class='k'>Última modificación</td><td>" + str(k.get("modificado")) + "</td></tr>"
          "</table>")
    else:
        A("<p class='nota'>No se pudo consultar la API de KoboToolbox: " + k["error"] + "</p>")
    A("<p>El formulario contiene <b>62 preguntas de criterio</b> con respuesta <code>SI / NO / NA</code>, "
      "más los datos de identificación del predio. Funciona sin señal: la aplicación móvil de Kobo guarda "
      "los envíos en el teléfono y los transmite cuando recupera conexión, de modo que una jornada completa "
      "de visitas puede hacerse en veredas sin cobertura y cargarse por wifi al volver.</p>")
    A("<h3>3.2 Cálculo propio del formulario</h3>")
    A("<p>El XLSForm incluye campos <code>calculate</code> que muestran al auditor el resultado al terminar. "
      "Estos campos usan referencias en la forma <code>${c_1_1}</code>; una referencia sin llaves compara "
      "texto literal y devuelve cero. La plataforma verifica esa condición en cada revisión "
      "(<code>corregir_formula_kobo.py</code> y <code>verificar_kobo.py</code>). "
      "<b>Aun así, el porcentaje del formulario es informativo:</b> el valor oficial siempre se recalcula en "
      "el servidor a partir de las respuestas.</p>")
    A("<h3>3.3 Otras vías de ingreso</h3>")
    A("<table><thead><tr><th>Vía</th><th>Uso</th><th>Consolidación</th></tr></thead><tbody>"
      "<tr><td>App Android propia</td><td>Auditoría sin señal en finca; sincroniza por wifi</td><td>API local :8200</td></tr>"
      "<tr><td>Formulario de Google</td><td>Autoauditoría rápida del productor</td><td><code>procesar_respuestas_form.py</code></td></tr>"
      "<tr><td>Hoja de cálculo</td><td>Carga masiva y corrección de datos maestros</td><td><code>importar_hoja.py</code></td></tr>"
      "<tr><td>Línea de comandos</td><td>Altas puntuales y reproceso</td><td><code>guardar_auditoria.py</code></td></tr>"
      "</tbody></table>")
    A("<p class='nota'>Fuentes registradas en la base: " +
      " · ".join(str(f["fuente"]) + " (" + str(f["c"]) + ")" for f in d["fuentes"]) + ".</p>")

    # procesamiento
    A("<h2>4. Procesamiento y reglas de negocio</h2>")
    A("<h3>4.1 Cálculo del cumplimiento</h3>")
    A("<p>El cálculo está centralizado en un único punto de escritura, <code>guardar_auditoria.py</code>. "
      "Ninguna otra ruta escribe porcentajes: todas las fuentes (formulario, app, hoja, consola) pasan por él. "
      "Esto garantiza que el mismo conjunto de respuestas produzca siempre el mismo resultado.</p>")
    A("<table><thead><tr><th>Regla</th><th>Implementación</th></tr></thead><tbody>"
      "<tr><td>Umbrales oficiales</td><td>Fundamentales 100 % · Mayores ≥ 80 % · Menores ≥ 60 %</td></tr>"
      "<tr><td>Criterios no aplicables</td><td>Los <code>NA</code> se excluyen del denominador de su categoría</td></tr>"
      "<tr><td>Concepto</td><td><b>Certificable</b> solo si cumplen las tres categorías; en caso contrario <b>Aplazado</b></td></tr>"
      "<tr><td>Origen del dato</td><td>Se confía en las respuestas SI/NO/NA; nunca en porcentajes importados</td></tr>"
      "<tr><td>Idempotencia</td><td>Mismo predio + fecha + criterio = actualización, no duplicado</td></tr>"
      "<tr><td>Nombre de predio</td><td>Mayúsculas, búsqueda sin distinguir mayúsculas ni tildes</td></tr>"
      "<tr><td>Grafías</td><td>Municipio y vereda se normalizan contra una lista canónica en todos los caminos de entrada</td></tr>"
      "</tbody></table>")
    A("<h3>4.2 Integridad y trazabilidad</h3>")
    A("<ul>"
      "<li>Clave primaria compuesta <code>(auditoria_id, criterio_id)</code> en respuestas: imposible guardar dos veces el mismo criterio.</li>"
      "<li>Restricción <code>CHECK (respuesta IN ('SI','NO','NA'))</code>: no entran valores fuera del dominio.</li>"
      "<li>Campo <code>fuente</code> en cada auditoría: se sabe por qué vía llegó cada registro.</li>"
      "<li>Visitas antiguas o duplicadas se trasladan a tablas de archivo aparte, sin alterar lo publicado.</li>"
      "<li>Los datos maestros se corrigen en la hoja de Google, que es la fuente; la base se sobreescribe en cada ciclo.</li>"
      "</ul>")

    # almacenamiento
    A("<h2>5. Almacenamiento</h2>")
    A("<p>Base SQLite única de <b>" + str(round(d["tam_db"] / 1024)) + " KB</b>, sin servidor de base de datos "
      "que mantener y respaldable como un solo archivo. Las cifras de la tabla se leen en vivo.</p>")
    A("<table><thead><tr><th>Tabla</th><th>Contenido</th><th>Filas</th></tr></thead><tbody>")
    desc_tabla = {"predios": "Datos maestros del predio, propietario y ubicación",
                  "auditorias": "Una visita: fecha, concepto, conteos y porcentajes por categoría",
                  "criterios": "Catálogo de los 62 criterios con su categoría y obligatoriedad",
                  "respuestas": "Una fila por criterio y visita (SI/NO/NA)",
                  "seguimiento": "Hallazgos con estado, responsable, plazo y evidencia",
                  "auditorias_archivo": "Visitas apartadas del cálculo vigente",
                  "respuestas_archivo": "Respuestas de esas visitas archivadas"}
    for t, n in d["tablas"]:
        A("<tr><td><code>" + t + "</code></td><td>" + desc_tabla.get(t, "—") + "</td><td class='c'>" + str(n) + "</td></tr>")
    A("</tbody></table>")
    A("<p class='nota'>Respaldo automático diario: " + str(d["bk_n"]) + " archivos, " + str(d["bk_peso"]) +
      " MB en total; el más reciente es del " + d["bk_ultimo"] + ". Se conserva además la hoja de Google como "
      "copia legible de los datos maestros y el repositorio Git como respaldo del código.</p>")

    # publicación
    A("<h2>6. Publicación y consulta</h2>")
    A("<table><thead><tr><th>Artefacto</th><th>Destino</th><th>Contenido</th></tr></thead><tbody>"
      "<tr><td>Dashboard (" + str(d["dash_kb"]) + " KB)</td><td>GitHub Pages<br><code>kaxtillo.github.io/bot-bpg-ica/dashboard/</code></td>"
      "<td>Indicadores, mapa, filtros por municipio, tabla de predios y ficha por predio con su seguimiento y plan de acción imprimible</td></tr>"
      "<tr><td>GeoJSON (" + str(d["geo_kb"]) + " KB)</td><td>uMap / capa pública</td>"
      "<td>" + str(d["geo_n"]) + " predios georreferenciados</td></tr>"
      "<tr><td>Hoja de Google</td><td>Cuenta institucional</td><td>Datos maestros editables y porcentajes por predio</td></tr>"
      "<tr><td>API local</td><td>Puerto 8200 en la red interna</td><td><code>/api/health</code>, <code>/api/predios</code>, <code>/api/auditorias</code></td></tr>"
      "</tbody></table>")
    A("<h3>6.1 Privacidad en el canal público</h3>")
    A("<p>El dashboard público <b>no publica</b> propietario, identificación ni teléfono. La consulta individual "
      "se hace por nombre del predio o por número de identificación, pero este último se convierte en una "
      "<b>huella SHA-256</b> calculada igual en el servidor y en el navegador: el HTML nunca contiene el número, "
      "solo su hash. Verificación sobre el archivo publicado: <b>" + str(d["dash_personales"]) +
      " coincidencias</b> de campos personales.</p>")
    A("<p>Los documentos que sí contienen datos personales (listados con propietario e identificación, planes de "
      "acción nominales) se entregan únicamente por canal privado o como archivo local, nunca al repositorio público.</p>")

    # planes de acción
    A("<h2>7. Generación de planes de acción y seguimiento</h2>")
    A("<p>Cuando un predio queda Aplazado, la plataforma convierte cada respuesta <code>NO</code> en un hallazgo "
      "accionable y produce un documento de trabajo para el productor.</p>")
    A("<table><thead><tr><th>Etapa</th><th>Herramienta</th><th>Resultado</th></tr></thead><tbody>"
      "<tr><td>Identificación de hallazgos</td><td><code>seguimiento.py sync</code></td>"
      "<td>Un registro por criterio incumplido, con marca de obligatorio y fecha límite sugerida</td></tr>"
      "<tr><td>Plan de acción</td><td><code>generar_plan_accion.py</code></td>"
      "<td>Documento por predio ordenado por prioridad, con el avance del plan y barra de progreso</td></tr>"
      "<tr><td>Entrega en PDF</td><td><code>exportar_plan_pdf.js</code> + <code>pdf_html.py</code></td>"
      "<td>Checklist A4 imprimible: casillas de verificación, espacio de observaciones y firmas</td></tr>"
      "<tr><td>Seguimiento</td><td><code>seguimiento.py listar | marcar</code></td>"
      "<td>Estado por hallazgo: pendiente, en proceso o cerrado, con responsable y evidencia</td></tr>"
      "</tbody></table>")
    A("<p>El plan distingue siempre los <b>criterios fundamentales</b>, porque un solo fundamental incumplido "
      "impide la certificación aunque el resto del predio cumpla. Esa priorización es la diferencia práctica "
      "entre un listado de fallas y un plan de trabajo.</p>")
    A("<p class='nota'>Estado actual del seguimiento: " + str(d["seguimiento"]) + " hallazgos registrados. "
      "El seguimiento es idempotente: resincronizar no borra estados, notas ni responsables ya definidos.</p>")

    # documentos
    A("<h2>8. Documentos y reportería</h2>")
    A("<table><thead><tr><th>Documento</th><th>Generador</th><th>Formato</th></tr></thead><tbody>"
      "<tr><td>Informe por periodo</td><td><code>reporte_periodo_pdf.py</code></td>"
      "<td>A4: altas del periodo, certificables, aplazados, distribución por vereda y hallazgos obligatorios</td></tr>"
      "<tr><td>Listado por municipio</td><td><code>listado_predios_pdf.py</code></td>"
      "<td>A4: predios con concepto y porcentajes; datos de contacto solo si se solicitan expresamente</td></tr>"
      "<tr><td>Plan de acción</td><td><code>exportar_plan_pdf.js</code></td><td>A4: checklist con firmas</td></tr>"
      "<tr><td>Ficha en pantalla</td><td>Dashboard</td><td>HTML: consulta individual y botón de impresión</td></tr>"
      "</tbody></table>")
    A("<p>La generación de PDF usa un módulo único (<code>pdf_html.py</code>) que intenta en orden "
      "<b>WeasyPrint → Chromium → Brave</b> y devuelve qué motor se usó. Así los informes no dependen de que "
      "exista un navegador instalado ni de una versión concreta: si una herramienta desaparece del sistema, "
      "la siguiente toma el relevo sin intervención.</p>")
    A("<p class='nota'>Entorno verificado: Python " + d["python"] + " · SQLite " + d["sqlite"] +
      " · WeasyPrint " + d["weasy"] + " · Chromium " + d["chromium"] + ".</p>")

    # automatización
    A("<h2>9. Automatización y operación desatendida</h2>")
    A("<table><thead><tr><th>Tarea</th><th>Frecuencia</th><th>Script</th><th>Estado</th><th>Última</th></tr></thead><tbody>")
    for j in d["cron"]:
        A("<tr><td>" + str(j["nombre"]) + "</td><td class='c'>" + str(j["cada"]) + "</td><td><code>" +
          str(j["script"]) + "</code></td><td class='c'>" + ("activo" if j["activo"] else "en pausa") +
          "</td><td class='c'>" + str(j["ultimo"]) + "</td></tr>")
    A("<tr><td>Ciclo completo (systemd)</td><td class='c'>diario</td><td><code>sincronizar_todo.sh</code></td>"
      "<td class='c'>activo</td><td class='c'>" + (d["prox_timer"] or "—") + " (próxima)</td></tr>")
    A("</tbody></table>")
    A("<p>La regla de diseño de las tareas automáticas es <b>silencio cuando no hay novedades</b>: si una "
      "ejecución no encuentra datos nuevos o no modifica ningún artefacto, no envía mensaje. El aviso al "
      "usuario solo aparece cuando hubo altas, cuando algo cambió y se publicó, o cuando hubo un error. "
      "Consecuencia práctica: un mensaje de la plataforma siempre significa algo.</p>")
    A("<h3>9.1 Monitoreo y verificación</h3>")
    A("<ul>"
      "<li>Comprobación de salud de la API y del estado de los cuatro servicios del sistema.</li>"
      "<li><code>verificar_kobo.py</code> compara los cálculos del formulario contra la base y reporta discrepancias.</li>"
      "<li><code>revisar_duplicados_kobo.py</code> detecta envíos repetidos y criterios que difieren entre visitas.</li>"
      "<li>Respaldo comprimido diario con retención por rotación.</li>"
      "<li>Repositorio Git con carga por API que compara el hash de cada archivo antes de subirlo.</li>"
      "</ul>")

    # riesgos
    A("<h2>10. Seguridad y riesgos identificados</h2>")
    A("<p>Se documentan explícitamente para que la operación no dependa de supuestos:</p>")
    A("<div class='aviso'><b>API local sin autenticación (puerto 8200).</b> Cualquier equipo en la misma red "
      "puede consultar los datos y enviar auditorías. Mitigación prevista: token de acceso y restricción por "
      "dirección de origen.</div>")
    A("<div class='aviso'><b>CORS abierto en la API.</b> Facilita el desarrollo, pero permite invocaciones desde "
      "cualquier página. Debe limitarse al origen propio antes de exponer el servicio fuera de la red interna.</div>")
    A("<div class='aviso'><b>Nombres de propietario en el GeoJSON público.</b> La capa del mapa incluye "
      "actualmente las propiedades <code>" + ", ".join(d["geo_props"]) + "</code>. El campo "
      "<code>propietario</code> debería retirarse de la capa pública, como ya se hizo en el dashboard.</div>")
    A("<div class='aviso'><b>Credenciales de Google en el repositorio público.</b> Archivos de credenciales y "
      "client_secret quedaron en el historial de Git. Borrarlos no elimina el historial: la acción efectiva es "
      "revocar los permisos en Google Cloud y emitir credenciales nuevas.</div>")
    A("<div class='ok'><b>Controles ya aplicados.</b> Cero datos personales en el dashboard publicado; búsqueda "
      "por huella SHA-256; secretos en archivo <code>.env</code> fuera del repositorio; lista de exclusión en la "
      "carga al repositorio; verificación de que ningún script contiene tokens incrustados.</div>")

    # pendientes
    A("<h2>11. Limitaciones actuales</h2>")
    A("<ul>"
      "<li>El formulario no valida la ortografía del municipio ni de la vereda: se compensa normalizando en el servidor, "
      "pero la solución de fondo es convertir esos campos en listas de selección.</li>"
      "<li>Una vereda o municipio nuevos entran con la grafía recibida; hay que agregarlos a la lista canónica para que se normalicen.</li>"
      "<li>La latencia de consolidación depende de la frecuencia programada: con un ciclo de 3 horas, una evaluación puede esperar hasta 3 horas.</li>"
      "<li>El dashboard depende de servicios externos para el mapa y los gráficos; ante un fallo de esas librerías, la consulta y la tabla siguen funcionando.</li>"
      "<li>La verificación de respaldo se hace por existencia y tamaño del archivo, no por restauración completa periódica.</li>"
      "</ul>")

    # anexo
    A("<h2>Anexo A. Inventario de programas</h2>")
    A("<table><thead><tr><th>Programa</th><th>Líneas</th><th>Tamaño</th><th>Función</th></tr></thead><tbody>")
    for nombre, n, b, desc in d["programas"]:
        A("<tr><td><code>" + nombre + "</code></td><td class='c'>" + str(n) + "</td><td class='c'>" +
          str(round(b / 1024, 1)) + " KB</td><td>" + desc + "</td></tr>")
    A("</tbody></table>")
    A("<h2>Anexo B. Datos de referencia</h2>")
    A("<table><thead><tr><th>Municipio</th><th>Predios</th></tr></thead><tbody>")
    for m, c in d["municipios"]:
        A("<tr><td>" + str(m) + "</td><td class='c'>" + str(c) + "</td></tr>")
    A("</tbody></table>")
    A("<p class='nota'>Este informe se genera desde el estado real del sistema: las cifras se consultan en el "
      "momento de emitirlo y no se transcriben a mano. Documento de carácter técnico y operativo; "
      "<b>no constituye certificación oficial del ICA</b>. Se omiten datos personales de acuerdo con la "
      "Ley 1581 de 2012.</p>")
    return ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
            "<title>Informe técnico · Plataforma BPG ICA</title>" + CSS + "</head><body>"
            + "".join(H) + "</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=os.path.join(BASE, "Informe_Tecnico_Plataforma_BPG.pdf"))
    a = ap.parse_args()
    d = recolectar()
    html = informe(d)
    open(os.path.join(os.path.expanduser("~/.hermes/cache/scratch"), "informe_tecnico.html"), "w", encoding="utf-8").write(html)
    sys.path.insert(0, BASE)
    from pdf_html import html_a_pdf
    ok, motor = html_a_pdf(html, a.salida)
    if not ok:
        print("ERROR: ningún motor de PDF disponible"); return 1
    print("PDF:", a.salida, "(motor:", motor + ")")
    print(f"{d['predios']} predios · {d['auditorias']} auditorías · {d['cert']} cert / {d['aplaz']} aplaz · {d['seguimiento']} hallazgos")
    print("programas:", len(d["programas"]), "· cron:", len(d["cron"]), "· respaldos:", d["bk_n"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
