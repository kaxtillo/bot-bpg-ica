#!/usr/bin/env python3
"""
informe_hallazgos_pdf.py — Informe de hallazgos e incumplimiento (A4).

Responde a tres preguntas:
  1. ¿Qué criterios se incumplen más y en qué proporción?
  2. ¿Qué está bloqueando la certificación hoy?
  3. ¿Qué acciones de mejora hay que priorizar, y cuánto le falta a cada predio?

Se calcula sobre el ESTADO ACTUAL de cada predio (su última auditoría), excluyendo los
criterios no aplicables (NA) del denominador, igual que en el cálculo oficial.

Uso:  informe_hallazgos_pdf.py [--salida ruta.pdf]
"""
import argparse, datetime, json, math, os, sqlite3, sys

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
UMBRAL = {"F": 100.0, "My": 80.0, "Mn": 60.0}

# Acción sugerida por criterio crítico. Se escribe a mano porque la recomendación
# automática no sirve: cada criterio tiene una salida técnica concreta.
ACCIONES = {
    "1.2": ("Gestionar la certificación de hato libre de brucelosis y tuberculosis ante el ICA "
            "(requisito documental, no de infraestructura). Conviene gestionarla por vereda en "
            "campaña conjunta para reducir el costo del muestreo.", "Medio", "Documental"),
    "2.1": ("Identificar todos los animales con arete o dispositivo oficial y abrir el registro "
            "individual; verificar que la identificación coincida con el RSPP del predio.", "Bajo", "Manejo"),
    "3.5": ("Señalizar potreros, corrales, sala de ordeño y bodegas con el uso y las restricciones "
            "de cada área (tiempos de retiro, tránsito, acceso restringido).", "Bajo", "Infraestructura"),
    "8.7": ("Implementar plan de control de plagas con mapa de estaciones, producto autorizado, "
            "cronograma y registro firmado; conservar las facturas del servicio.", "Medio", "Documental"),
    "7.7": ("Analizar la calidad del agua de bebida y de lavado (fisicoquímico y microbiológico), "
            "limpiar tanques y dejar el resultado dentro del expediente del predio.", "Medio", "Documental"),
    "9.7": ("Documentar el protocolo de sacrificio humanitario: método aprobado, personal entrenado "
            "y registro de aplicación.", "Bajo", "Documental"),
    "6.10": ("Llevar libro de inventario de productos veterinarios con lote, fecha de vencimiento, "
             "entradas y salidas; separar y rotular productos vencidos para disposición.", "Bajo", "Documental"),
    "7.6": ("Llevar registro de inventario de alimentos y forrajes: entradas, salidas, rotación y "
            "condiciones de almacenamiento.", "Bajo", "Documental"),
    "8.5": ("Definir el manejo de residuos y la disposición de animales muertos conforme a la norma, "
            "con sitio identificado y registro.", "Medio", "Infraestructura"),
    "2.2": ("Abrir registro individual por animal (nacimiento, tratamientos, producción) y mantenerlo "
            "actualizado; puede ser en planilla o aplicación.", "Bajo", "Manejo"),
    "1.6": ("Adecuar el área de enfermería: espacio independiente, lavable, con botiquín, "
            "medicamentos separados y registro de atención.", "Medio", "Infraestructura"),
    "1.7": ("Implementar el programa de control de mastitis: prueba de CMT periódica, registro de "
            "casos y protocolo de tratamiento de vaca seca.", "Medio", "Manejo"),
    "1.5": ("Elaborar el instructivo de manejo de enfermedades con signos, acciones y responsable; "
            "socializarlo con el personal.", "Bajo", "Documental"),
    "1.4": ("Registrar los diagnósticos veterinarios con fecha, animal, hallazgo e indicación.", "Bajo", "Documental"),
    "1.3": ("Escribir y aplicar el protocolo de aislamiento de animales enfermos o nuevos.", "Bajo", "Documental"),
    "1.1": ("Actualizar el plan sanitario anual aprobado por veterinario, con calendario de vacunación "
            "y desparasitación ejecutado.", "Bajo", "Documental"),
    "6.7": ("Exigir y archivar la prescripción veterinaria de cada tratamiento aplicado.", "Bajo", "Documental"),
    "4.7": ("Documentar la disposición de la leche anormal (animal en tratamiento o mastitis): "
            "destino, recipiente identificado y registro.", "Bajo", "Manejo"),
    "4.2": ("Adecuar las instalaciones de ordeño fijo según la norma: superficies lavables, "
            "separación de áreas y ventilación.", "Alto", "Infraestructura"),
    "4.5": ("Estandarizar la rutina de ordeño por escrito y capacitar al ordeñador: aseo de pezones, "
            "sellado, orden de ordeño.", "Bajo", "Manejo"),
    "4.6": ("Verificar y registrar la limpieza y el mantenimiento de equipos y utensilios de ordeño.", "Bajo", "Manejo"),
}

CSS = """<style>
@page{size:A4 portrait;margin:11mm 12mm 13mm 12mm;
  @bottom-left{content:"Informe de hallazgos · BPG ICA 067449";font-size:7.5pt;color:#7a8a84}
  @bottom-right{content:"Página " counter(page) " de " counter(pages);font-size:7.5pt;color:#7a8a84}}
*{box-sizing:border-box}
body{font-family:'DejaVu Sans',Arial,sans-serif;color:#1b2b26;margin:0;font-size:8.8pt;line-height:1.4}
.portada{background:#0B3D2E;color:#fff;padding:14px 16px;border-radius:5px;margin-bottom:10px}
.portada h1{margin:0 0 3px;font-size:16pt}
.portada .s{font-size:9.5pt;opacity:.93}
.portada .m{font-size:8pt;opacity:.85;margin-top:7px;border-top:1px solid rgba(255,255,255,.35);padding-top:5px}
h2{font-size:11.5pt;color:#0B3D2E;margin:12px 0 5px;border-bottom:1.4px solid #0B3D2E;padding-bottom:2px;page-break-after:avoid}
h3{font-size:9.6pt;color:#155443;margin:9px 0 3px;page-break-after:avoid}
p{margin:3px 0 5px;text-align:justify}
table{width:100%;border-collapse:collapse;margin:4px 0 6px}
thead{display:table-header-group}tr{page-break-inside:avoid}
th,td{border:1px solid #c3cfc9;padding:2.4px 4px;font-size:8.1pt;vertical-align:top}
th{background:#eef3f0;text-align:left;font-size:7.5pt;text-transform:uppercase;letter-spacing:.3px}
td.c{text-align:center;white-space:nowrap}td.n{text-align:right;white-space:nowrap}
.cifras{width:100%;border-collapse:separate;border-spacing:6px 0;margin:5px 0 8px}
td.cif{border:1px solid #cfdad5;border-top:3.5px solid #0B3D2E;border-radius:4px;padding:5px 8px;background:#f7faf8;width:25%}
td.cif .n{font-size:15pt;font-weight:700;color:#0B3D2E;line-height:1.05}
td.cif .l{font-size:7.3pt;color:#5b6b66;text-transform:uppercase;letter-spacing:.3px}
td.cif.r{border-top-color:#C62828}td.cif.r .n{color:#C62828}
td.cif.a{border-top-color:#EF6C00}td.cif.a .n{color:#EF6C00}
.barra{background:#e8eeeb;border-radius:2px;height:8px;width:100%;overflow:hidden}
.barra span{display:block;height:8px;background:#C62828}
.barra.m span{background:#EF6C00}
.barra.b span{background:#1565C0}
.aviso{border-left:4px solid #C62828;background:#fdf3f2;padding:6px 9px;margin:6px 0;font-size:8.4pt}
.ok{border-left:4px solid #2E7D32;background:#f2f8f3;padding:6px 9px;margin:6px 0;font-size:8.4pt}
.info{border-left:4px solid #1565C0;background:#f2f6fc;padding:6px 9px;margin:6px 0;font-size:8.4pt}
.nota{font-size:7.8pt;color:#546e64;margin-top:2px}
code{font-family:'DejaVu Sans Mono',monospace;font-size:7.9pt;background:#eef2f0;padding:0 2px;border-radius:2px}
</style>"""


def datos():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    ultimas = con.execute("""
        SELECT p.id, p.nombre, p.municipio, p.vereda, a.id AS aud, a.fecha, a.concepto
        FROM predios p
        JOIN auditorias a ON a.id = (SELECT id FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC, id DESC LIMIT 1)
    """).fetchall()
    tipos = dict(con.execute("SELECT id, tipo FROM criterios").fetchall())
    nombres = dict(con.execute("SELECT id, nombre FROM criterios").fetchall())

    por_crit = {}
    for p in ultimas:
        for cid, r in con.execute("SELECT criterio_id, respuesta FROM respuestas WHERE auditoria_id=?", (p["aud"],)):
            if r == "NA":
                continue
            d = por_crit.setdefault(cid, {"SI": 0, "NO": 0, "predios": []})
            d[r] += 1
            if r == "NO":
                d["predios"].append(p["nombre"])
    criterios = []
    for cid, d in por_crit.items():
        tot = d["SI"] + d["NO"]
        if tot:
            criterios.append({"id": cid, "tipo": tipos.get(cid, "?"), "nombre": nombres.get(cid, cid),
                              "no": d["NO"], "tot": tot, "pct": d["NO"] / tot * 100, "predios": d["predios"]})
    criterios.sort(key=lambda x: (-x["no"], -x["pct"]))

    # cuánto le falta a cada predio para certificar
    rutas = []
    for p in ultimas:
        if p["concepto"] == "Certificable":
            continue
        calc = {"F": [0, 0], "My": [0, 0], "Mn": [0, 0]}
        for cid, r in con.execute("SELECT criterio_id, respuesta FROM respuestas WHERE auditoria_id=?", (p["aud"],)):
            t = tipos.get(cid)
            if t in calc and r != "NA":
                calc[t][1] += 1
                if r == "SI":
                    calc[t][0] += 1
        falta = {}
        for t, (cum, tot) in calc.items():
            if not tot:
                falta[t] = 0
                continue
            if t == "F":
                falta[t] = tot - cum
            else:
                necesarios = math.ceil(UMBRAL[t] / 100 * tot - cum)
                falta[t] = max(0, necesarios)
        rutas.append({"nombre": p["nombre"], "vereda": p["vereda"], "fecha": p["fecha"],
                      "falta": falta, "total": sum(falta.values()),
                      "pct": {t: (calc[t][0] / calc[t][1] * 100 if calc[t][1] else 0) for t in calc}})
    rutas.sort(key=lambda x: x["total"])

    veredas = {}
    for p in ultimas:
        h = sum(1 for c in criterios if p["nombre"] in c["predios"])
        v = veredas.setdefault(p["vereda"] or "—", {"n": 0, "hall": 0})
        v["n"] += 1
        v["hall"] += h
    return {"ultimas": ultimas, "criterios": criterios, "rutas": rutas, "veredas": veredas}


def construir(d):
    H = []
    A = H.append
    crit = d["criterios"]
    total_hall = sum(c["no"] for c in crit)
    total_ev = sum(c["tot"] for c in crit)
    pct_global = (total_hall / total_ev * 100) if total_ev else 0
    por_tipo = {t: {"no": sum(c["no"] for c in crit if c["tipo"] == t),
                    "tot": sum(c["tot"] for c in crit if c["tipo"] == t)} for t in ("F", "My", "Mn")}
    secciones = {}
    for c in crit:
        s = c["id"].split(".")[0]
        x = secciones.setdefault(s, {"no": 0, "tot": 0})
        x["no"] += c["no"]
        x["tot"] += c["tot"]
    hoy = datetime.date.today()
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]

    A("<div class='portada'><h1>Informe de hallazgos e incumplimiento</h1>"
      "<div class='s'>Buenas Prácticas Ganaderas · Resolución ICA 067449 · Forma 3-852 V6</div>"
      "<div class='m'>Calculado sobre el estado actual de " + str(len(d["ultimas"])) +
      " predios (última auditoría de cada uno) · " + f"{hoy.day} de {meses[hoy.month-1]} de {hoy.year}" +
      "</div></div>")

    A("<h2>1. Resumen</h2>")
    A("<table class='cifras'><tr>"
      "<td class='cif'><div class='n'>" + str(len(d["ultimas"])) + "</div><div class='l'>Predios evaluados</div></td>"
      "<td class='cif r'><div class='n'>" + str(total_hall) + "</div><div class='l'>Incumplimientos</div></td>"
      "<td class='cif r'><div class='n'>" + f"{pct_global:.1f}%".replace(".", ",") + "</div><div class='l'>Incumplimiento global</div></td>"
      "<td class='cif a'><div class='n'>" + str(len(d["rutas"])) + "</div><div class='l'>Predios por certificar</div></td>"
      "</tr></table>")
    A("<table><thead><tr><th>Categoría</th><th>Incumplimientos</th><th>Evaluaciones</th>"
      "<th>% incumplimiento</th><th>Máximo admisible</th><th>Barra</th></tr></thead><tbody>")
    etq = {"F": "Fundamentales", "My": "Mayores", "Mn": "Menores"}
    for t in ("F", "My", "Mn"):
        x = por_tipo[t]
        pct = x["no"] / x["tot"] * 100 if x["tot"] else 0
        clase = "b" if t == "F" else ("m" if t == "My" else "")
        A("<tr><td><b>" + etq[t] + "</b></td><td class='c'>" + str(x["no"]) + "</td><td class='c'>" +
          str(x["tot"]) + "</td><td class='c'>" + f"{pct:.1f}%".replace(".", ",") + "</td><td class='c'>" +
          ("0%" if t == "F" else ("≤ 20%" if t == "My" else "≤ 40%")) + "</td>"
          "<td><div class='barra " + clase + "'><span style='width:" + f"{min(100, pct):.1f}" +
          "%'></span></div></td></tr>")
    A("</tbody></table>")
    A("<p class='nota'>Los criterios marcados como no aplicables (NA) se excluyen del denominador. "
      "En Fundamentales el umbral es 100%: un solo incumplimiento impide certificar.</p>")

    A("<h2>2. Criterios con mayor incumplimiento</h2>")
    A("<p>Ranking sobre el estado actual de los predios. La columna de predios permite dimensionar el "
      "alcance: un criterio con 90% de incumplimiento es un problema sistémico, no de un productor.</p>")
    A("<table><thead><tr><th>#</th><th>Criterio</th><th>Nombre</th><th>Tipo</th><th>Predios</th>"
      "<th>% incumpl.</th><th>Proporción</th></tr></thead><tbody>")
    for i, c in enumerate(crit[:18], 1):
        aviso_muestra = " <span class='nota'>(muestra pequeña)</span>" if c["tot"] < 10 else ""
        A("<tr><td class='c'>" + str(i) + "</td><td class='c'><code>" + c["id"] + "</code></td><td>" +
          c["nombre"] + aviso_muestra + "</td><td class='c'>" + c["tipo"] + "</td><td class='c'>" + str(c["no"]) + "/" +
          str(c["tot"]) + "</td><td class='c'>" + f"{c['pct']:.1f}%".replace(".", ",") + "</td>"
          "<td style='width:26%'><div class='barra'><span style='width:" + f"{c['pct']:.1f}" + "%'></span></div></td></tr>")
    A("</tbody></table>")
    top = max(crit, key=lambda c: c["no"]) if crit else None
    if top:
        A("<div class='aviso'><b>El hallazgo dominante es el " + top["id"] + " — " + top["nombre"] +
          ":</b> lo incumplen <b>" + str(top["no"]) + " de " + str(top["tot"]) + " predios (" +
          f"{top['pct']:.1f}%".replace(".", ",") + ")</b>. No es un problema de manejo individual: "
          "es un requisito que casi ningún predio ha gestionado y que se resuelve por gestión "
          "colectiva, no finca por finca.</div>")

    A("<h2>3. Dónde se concentra el incumplimiento</h2>")
    A("<h3>Por sección de la norma</h3>")
    A("<table><thead><tr><th>Sección</th><th>Incumplimientos</th><th>Evaluaciones</th><th>% </th><th>Proporción</th></tr></thead><tbody>")
    SECCIONES = {"1": "Sanidad animal y bioseguridad", "2": "Identificación y trazabilidad",
                 "3": "Instalaciones y áreas", "4": "Ordeño y leche", "5": "Almacenamiento",
                 "6": "Medicamentos veterinarios", "7": "Alimentación", "8": "Saneamiento ambiental",
                 "9": "Bienestar animal", "10": "Personal"}
    for s in sorted(secciones, key=lambda x: -secciones[x]["no"]):
        x = secciones[s]
        pct = x["no"] / x["tot"] * 100 if x["tot"] else 0
        A("<tr><td><b>" + s + ". " + SECCIONES.get(s, "") + "</b></td><td class='c'>" + str(x["no"]) +
          "</td><td class='c'>" + str(x["tot"]) + "</td><td class='c'>" + f"{pct:.1f}%".replace(".", ",") +
          "</td><td style='width:26%'><div class='barra'><span style='width:" + f"{min(100, pct):.1f}" +
          "%'></span></div></td></tr>")
    A("</tbody></table>")
    A("<h3>Por vereda</h3>")
    A("<table><thead><tr><th>Vereda</th><th>Predios</th><th>Hallazgos</th><th>Promedio por predio</th></tr></thead><tbody>")
    for v, x in sorted(d["veredas"].items(), key=lambda kv: -(kv[1]["hall"] / kv[1]["n"] if kv[1]["n"] else 0)):
        prom = x["hall"] / x["n"] if x["n"] else 0
        A("<tr><td>" + v + "</td><td class='c'>" + str(x["n"]) + "</td><td class='c'>" + str(x["hall"]) +
          "</td><td class='c'>" + f"{prom:.1f}".replace(".", ",") + "</td></tr>")
    A("</tbody></table>")
    A("<p class='nota'>Una vereda con promedio alto necesita acompañamiento colectivo (jornada de "
      "extensión), no visitas correctivas predio por predio.</p>")

    A("<h2>4. Qué está bloqueando la certificación</h2>")
    A("<p>Solo los criterios <b>Fundamentales</b> bloquean: exigen 100%. Estos son los que hoy tienen "
      "incumplimientos, ordenados por número de predios afectados.</p>")
    fundamentales = [c for c in crit if c["tipo"] == "F" and c["no"] > 0]
    fundamentales.sort(key=lambda c: -c["no"])
    A("<table><thead><tr><th>Criterio</th><th>Nombre</th><th>Predios afectados</th><th>Cuáles</th></tr></thead><tbody>")
    for c in fundamentales:
        A("<tr><td class='c'><code>" + c["id"] + "</code></td><td>" + c["nombre"] + "</td><td class='c'>" +
          str(c["no"]) + "</td><td>" + ", ".join(sorted(c["predios"])) + "</td></tr>")
    A("</tbody></table>")

    A("<h2>5. Ruta de certificación por predio</h2>")
    A("<p>Cuántos criterios debe corregir cada predio aplazado para alcanzar los tres umbrales. "
      "Es la lista de trabajo ordenada por esfuerzo: los primeros son los que están más cerca.</p>")
    A("<table><thead><tr><th>Predio</th><th>Vereda</th><th>Fundamentales a corregir</th>"
      "<th>Mayores a corregir</th><th>Menores a corregir</th><th>Total</th></tr></thead><tbody>")
    for r in d["rutas"]:
        A("<tr><td><b>" + r["nombre"] + "</b></td><td>" + (r["vereda"] or "—") + "</td><td class='c'>" +
          (str(r["falta"]["F"]) if r["falta"]["F"] else "—") + "</td><td class='c'>" +
          (str(r["falta"]["My"]) if r["falta"]["My"] else "—") + "</td><td class='c'>" +
          (str(r["falta"]["Mn"]) if r["falta"]["Mn"] else "—") + "</td><td class='c'><b>" +
          str(r["total"]) + "</b></td></tr>")
    A("</tbody></table>")
    cerca = [r for r in d["rutas"] if r["total"] <= 2]
    if cerca:
        A("<div class='ok'><b>Los más cerca de certificar:</b> " +
          "; ".join(r["nombre"] + " (" + str(r["total"]) + " criterio" + ("" if r["total"] == 1 else "s") + ")" for r in cerca) +
          ". Son las visitas con mayor retorno por hora de trabajo.</div>")

    A("<h2>6. Acciones de mejora recomendadas</h2>")
    A("<p>Para cada criterio crítico, la salida concreta. El tipo distingue lo que se resuelve con "
      "documentos y manejo (bajo costo) de lo que exige obra o inversión.</p>")
    A("<table><thead><tr><th>Criterio</th><th>Acción sugerida</th><th>Esfuerzo</th><th>Tipo</th>"
      "<th>Predios</th></tr></thead><tbody>")
    for c in crit:
        if c["id"] not in ACCIONES:
            continue
        acc, esfuerzo, tipo = ACCIONES[c["id"]]
        A("<tr><td class='c'><code>" + c["id"] + "</code><br><span class='nota'>" + c["nombre"] +
          "</span></td><td>" + acc + "</td><td class='c'>" + esfuerzo + "</td><td class='c'>" + tipo +
          "</td><td class='c'>" + str(c["no"]) + "</td></tr>")
    A("</tbody></table>")

    doc = [c for c in crit if c["id"] in ACCIONES and ACCIONES[c["id"]][2] == "Documental"]
    obra = [c for c in crit if c["id"] in ACCIONES and ACCIONES[c["id"]][2] == "Infraestructura"]
    A("<div class='info'><b>Prioridad recomendada.</b> " + str(len(doc)) +
      " de los criterios críticos se resuelven con <b>documentos y registros</b> (" +
      ", ".join(c["id"] for c in doc[:8]) + "), sin inversión en obra. Solo " + str(len(obra)) +
      " exigen intervención física (" + ", ".join(c["id"] for c in obra) + "). Empezar por el bloque "
      "documental permite subir el cumplimiento sin costo de infraestructura.</div>")

    A("<h2>7. Recomendación operativa</h2>")
    A("<ul>"
      "<li><b>Campaña colectiva del " + (top["id"] if top else "1.2") +
      ":</b> gestionar por vereda la certificación de hato libre; el costo del muestreo baja al "
      "hacerlo en grupo y desbloquea a la mayoría de los predios de una sola vez.</li>"
      "<li><b>Jornada de extensión en las veredas con mayor promedio:</b> " +
      ", ".join(f"{v} ({x['hall']/x['n']:.1f} por predio)" for v, x in
                sorted(d["veredas"].items(), key=lambda kv: -(kv[1]["hall"] / kv[1]["n"] if kv[1]["n"] else 0))[:3]) +
      ". El patrón se repite por zona, lo que sugiere una causa común y no casos aislados.</li>"
      "<li><b>Paquete documental estandarizado:</b> entregar a cada productor un kit con los formatos "
      "de registro (plan sanitario, tratamientos, inventarios, prescripciones) ya diligenciables; "
      "resuelve varios criterios críticos con un solo entregable.</li>"
      "<li><b>Revisitas priorizadas:</b> atender primero los predios que están a uno o dos criterios "
      "de certificar; el esfuerzo se convierte en certificaciones en el corto plazo.</li>"
      "</ul>")
    A("<p class='nota'>Informe calculado desde las respuestas SI/NO/NA de la última auditoría de cada "
      "predio; los porcentajes se recalculan en el servidor y no provienen de valores declarados. "
      "Documento de trabajo para orientar acciones de mejora; no constituye certificación oficial del ICA.</p>")
    return ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'><title>Informe de hallazgos BPG</title>"
            + CSS + "</head><body>" + "".join(H) + "</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=os.path.join(BASE, "Informe_Hallazgos_BPG.pdf"))
    a = ap.parse_args()
    d = datos()
    html = construir(d)
    os.makedirs(os.path.expanduser("~/.hermes/cache/scratch"), exist_ok=True)
    open(os.path.expanduser("~/.hermes/cache/scratch/informe_hallazgos.html"), "w", encoding="utf-8").write(html)
    sys.path.insert(0, BASE)
    from pdf_html import html_a_pdf
    ok, motor = html_a_pdf(html, a.salida)
    if not ok:
        print("ERROR: ningún motor de PDF disponible")
        return 1
    crit = d["criterios"]
    print("PDF:", a.salida, "(motor:", motor + ")")
    print(f"{len(d['ultimas'])} predios · {sum(c['no'] for c in crit)} incumplimientos · "
          f"{len(d['rutas'])} predios por certificar")
    print("top 3:", ", ".join(f"{c['id']} {c['nombre']} ({c['pct']:.0f}%)" for c in crit[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
