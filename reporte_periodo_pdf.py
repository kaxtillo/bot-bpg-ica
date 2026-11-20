#!/usr/bin/env python3
"""
reporte_periodo_pdf.py — Informe profesional (A4) de los predios evaluados en un periodo.

Uso:
    reporte_periodo_pdf.py [--desde 2026-11-19] [--hasta 2026-11-20] [--salida ruta.pdf]

"Predios que ingresaron" = predios cuya PRIMERA auditoría cae dentro del periodo.
Incluye además una sección con las visitas de seguimiento (predios que ya existían).
Genera el PDF con chromium headless (Brave falla aquí por el sandbox).
"""
import argparse, datetime, os, sqlite3, subprocess, sys

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
SCRATCH = os.path.expanduser("~/.hermes/cache/scratch")

CSS = """<style>
@page{size:A4 portrait;margin:14mm}
*{box-sizing:border-box}
body{font-family:'Segoe UI',Arial,sans-serif;color:#1b2b26;margin:0;font-size:10.5px}
.cab{background:#0B3D2E;color:#fff;padding:14px 16px;border-radius:4px}
.cab h1{margin:0;font-size:17px;letter-spacing:.3px}
.cab .sub{margin-top:3px;font-size:10.5px;opacity:.92}
.periodo{margin:10px 0 12px;font-size:11px;color:#37474F}
.kpis{width:100%;border-collapse:separate;border-spacing:8px 0;margin:0 0 12px}
td.kpi{width:25%;border:1px solid #cfdad5;border-top:4px solid #0B3D2E;border-radius:4px;padding:8px 10px;background:#f7faf8;vertical-align:top}
td.kpi .n{font-size:20px;font-weight:700;color:#0B3D2E;line-height:1.1}
td.kpi .l{font-size:9.5px;color:#5b6b66;text-transform:uppercase;letter-spacing:.4px}
td.kpi.verde{border-top-color:#2E7D32}td.kpi.verde .n{color:#2E7D32}
td.kpi.rojo{border-top-color:#C62828}td.kpi.rojo .n{color:#C62828}
h2{font-size:12px;color:#0B3D2E;margin:16px 0 6px;border-bottom:1px solid #cfdad5;padding-bottom:3px}
table{width:100%;border-collapse:collapse;margin-bottom:4px}
th,td{border:1px solid #c3cfc9;padding:4px 5px;font-size:9.8px;vertical-align:top}
th{background:#eef3f0;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:.3px}
td.c{text-align:center;white-space:nowrap}
td.n{text-align:right;white-space:nowrap}
.cert{color:#2E7D32;font-weight:600}
.apl{color:#C62828;font-weight:600}
tfoot td{background:#f2f6f4;font-weight:600}
.nota{font-size:9.3px;color:#546e64;margin-top:3px}
.pie{margin-top:16px;border-top:1px solid #c3cfc9;padding-top:7px;font-size:8.8px;color:#5b6b66;line-height:1.45}
.firma{width:100%;margin-top:22px;font-size:9.5px;border-collapse:separate;border-spacing:40px 0}
.firma td{border:0;border-top:1px solid #333;padding-top:4px}
</style>"""


def predios_del_periodo(con, desde, hasta):
    return con.execute("""
        SELECT p.id, p.nombre, p.propietario, p.municipio, p.vereda,
               MIN(a.fecha) AS primera,
               (SELECT concepto FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC,id DESC LIMIT 1) concepto,
               (SELECT f_cumplidos FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC,id DESC LIMIT 1) fc,
               (SELECT f_total FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC,id DESC LIMIT 1) ft,
               (SELECT f_pct FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC,id DESC LIMIT 1) fp,
               (SELECT my_pct FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC,id DESC LIMIT 1) myp,
               (SELECT mn_pct FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC,id DESC LIMIT 1) mnp,
               (SELECT COUNT(*) FROM respuestas r WHERE r.auditoria_id=
                   (SELECT id FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC,id DESC LIMIT 1)
                   AND r.respuesta='NO') hall,
               (SELECT COUNT(*) FROM respuestas r WHERE r.auditoria_id=
                   (SELECT id FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC,id DESC LIMIT 1)
                   AND r.respuesta='NO' AND r.criterio_id IN (SELECT id FROM criterios WHERE tipo='F')) hall_f
        FROM predios p JOIN auditorias a ON a.predio_id=p.id
        GROUP BY p.id HAVING primera BETWEEN ? AND ? ORDER BY p.vereda, p.nombre""",
        (desde, hasta)).fetchall()


def seguimiento(con, desde, hasta):
    return con.execute("""
        SELECT p.nombre, p.vereda, a.fecha, a.concepto
        FROM auditorias a JOIN predios p ON p.id=a.predio_id
        WHERE a.fecha BETWEEN ? AND ?
          AND (SELECT MIN(fecha) FROM auditorias WHERE predio_id=p.id) NOT BETWEEN ? AND ?
        ORDER BY a.fecha""", (desde, hasta, desde, hasta)).fetchall()


def fmt_fecha(f):
    try:
        d = datetime.date.fromisoformat(str(f)[:10])
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-11-19")
    ap.add_argument("--hasta", default="2026-11-20")
    ap.add_argument("--salida", default=None)
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    filas = predios_del_periodo(con, a.desde, a.hasta)
    if not filas:
        print("Sin predios en ese periodo."); return 1
    seg = seguimiento(con, a.desde, a.hasta)

    cert = [f for f in filas if f["concepto"] == "Certificable"]
    apl = [f for f in filas if f["concepto"] != "Certificable"]
    veredas = {}
    for f in filas:
        veredas.setdefault(f["vereda"] or "—", []).append(f)

    hoy = datetime.date.today().strftime("%d/%m/%Y")
    periodo = (fmt_fecha(a.desde) if a.desde == a.hasta
               else f"{fmt_fecha(a.desde)} al {fmt_fecha(a.hasta)}")

    # tabla de predios
    trs = []
    for i, f in enumerate(filas, 1):
        clase = "cert" if f["concepto"] == "Certificable" else "apl"
        trs.append("<tr><td class='c'>" + str(i) + "</td>"
                   + "<td><b>" + (f["nombre"] or "") + "</b></td>"
                   + "<td>" + (f["propietario"] or "—") + "</td>"
                   + "<td>" + (f["vereda"] or "—") + "</td>"
                   + "<td class='c'>" + fmt_fecha(f["primera"]) + "</td>"
                   + "<td class='" + clase + "'>" + (f["concepto"] or "") + "</td>"
                   + "<td class='n'>" + (str(f["fc"]) + "/" + str(f["ft"]) + " · " + str(round(f["fp"] or 0, 1)) + "%") + "</td>"
                   + "<td class='n'>" + str(round(f["myp"] or 0, 1)) + "%</td>"
                   + "<td class='n'>" + str(round(f["mnp"] or 0, 1)) + "%</td>"
                   + "<td class='c'>" + str(f["hall"]) + "</td></tr>")

    # por vereda
    tv = []
    for v, lst in sorted(veredas.items()):
        c = sum(1 for x in lst if x["concepto"] == "Certificable")
        tv.append("<tr><td>" + v + "</td><td class='c'>" + str(len(lst)) + "</td>"
                  + "<td class='c cert'>" + str(c) + "</td><td class='c apl'>" + str(len(lst) - c) + "</td></tr>")

    # hallazgos obligatorios pendientes
    th = []
    for f in sorted(filas, key=lambda x: -(x["hall_f"] or 0)):
        if f["hall_f"]:
            th.append("<tr><td><b>" + (f["nombre"] or "") + "</b></td><td class='c'>" + (f["vereda"] or "—") + "</td>"
                      + "<td class='c apl'>" + str(f["hall_f"]) + "</td><td class='c'>" + str(f["hall"]) + "</td></tr>")

    ts = ""
    if seg:
        filas_seg = "".join("<tr><td>" + (s["nombre"] or "") + "</td><td class='c'>" + (s["vereda"] or "—")
                            + "</td><td class='c'>" + fmt_fecha(s["fecha"]) + "</td><td class='c "
                            + ("cert" if s["concepto"] == "Certificable" else "apl") + "'>" + (s["concepto"] or "") + "</td></tr>"
                            for s in seg)
        ts = ("<h2>Visitas de seguimiento (predios ya registrados)</h2><table><thead><tr>"
              "<th>Predio</th><th>Vereda</th><th>Fecha</th><th>Concepto</th></tr></thead><tbody>"
              + filas_seg + "</tbody></table>"
              "<div class='nota'>Son revisiones de predios que ya estaban en el sistema; se contabilizan aparte "
              "para no duplicar el número de predios.</div>")

    html = ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
            "<title>Informe BPG " + periodo + "</title>" + CSS + "</head><body>"
            "<div class='cab'><h1>INFORME DE PREDIOS EVALUADOS EN BUENAS PRÁCTICAS GANADERAS</h1>"
            "<div class='sub'>Resolución ICA 067449 · Forma 3-852 V6 · Producción de leche · Departamento del Cauca</div></div>"
            "<div class='periodo'><b>Periodo del informe:</b> " + periodo
            + " &nbsp;·&nbsp; <b>Emitido:</b> " + hoy
            + " &nbsp;·&nbsp; <b>Fuente:</b> auditorías diligenciadas en el formulario digital (KoboToolbox) y consolidadas en la base de datos</div>"
            "<table class='kpis'><tr>"
            "<td class='kpi'><div class='n'>" + str(len(filas)) + "</div><div class='l'>Predios evaluados</div></td>"
            "<td class='kpi verde'><div class='n'>" + str(len(cert)) + "</div><div class='l'>Certificables</div></td>"
            "<td class='kpi rojo'><div class='n'>" + str(len(apl)) + "</div><div class='l'>Aplazados</div></td>"
            "<td class='kpi'><div class='n'>" + str(len(veredas)) + "</div><div class='l'>Veredas</div></td>"
            "</tr></table>"
            "<h2>1. Detalle de los predios</h2>"
            "<table><thead><tr><th>#</th><th>Predio</th><th>Propietario</th><th>Vereda</th><th>Fecha</th>"
            "<th>Concepto</th><th>Fundamentales</th><th>Mayores</th><th>Menores</th><th>Hallazgos</th></tr></thead>"
            "<tbody>" + "".join(trs) + "</tbody>"
            "<tfoot><tr><td colspan='5'>TOTAL: " + str(len(filas)) + " predios</td>"
            "<td class='c'>" + str(len(cert)) + " cert. / " + str(len(apl)) + " aplaz.</td>"
            "<td colspan='4'></td></tr></tfoot></table>"
            "<div class='nota'>Umbrales oficiales: Fundamentales 100% · Mayores ≥ 80% · Menores ≥ 60%. "
            "Los criterios no aplicables (NA) no entran en el cálculo.</div>"

            "<h2>2. Distribución por vereda</h2>"
            "<table><thead><tr><th>Vereda</th><th>Predios</th><th>Certificables</th><th>Aplazados</th></tr></thead><tbody>"
            + "".join(tv) + "</tbody></table>"

            + ("<h2>3. Hallazgos obligatorios pendientes</h2>"
               "<table><thead><tr><th>Predio</th><th>Vereda</th><th>Fundamentales incumplidos</th><th>Total hallazgos</th></tr></thead><tbody>"
               + "".join(th) + "</tbody></table>"
               "<div class='nota'>Un solo criterio fundamental incumplido impide la certificación, aunque el resto cumpla.</div>"
               if th else "")

            + ts +

            "<table class='firma'><tr><td>Profesional que emite el informe</td><td>Fecha</td></tr></table>"
            "<div class='pie'><b>Nota metodológica.</b> El informe se elabora a partir de las evaluaciones diligenciadas "
            "por el productor o el asesor en el formulario digital de auditoría y consolidadas automáticamente en la base de datos; "
            "el puntaje se recalcula desde las respuestas SI/NO/NA y no desde valores declarados. "
            "<b>Este documento corresponde a la preparación para la certificación en BPG y no constituye certificación oficial del ICA.</b> "
            "Los datos de contacto del productor se omiten por tratamiento de datos personales (Ley 1581 de 2012).</div>"
            "</body></html>")

    os.makedirs(SCRATCH, exist_ok=True)
    etiqueta = a.desde.replace("-", "") + "_" + a.hasta.replace("-", "")
    html_path = os.path.join(SCRATCH, "informe_" + etiqueta + ".html")
    salida = a.salida or os.path.join(BASE, "Informe_Predios_" + etiqueta + ".pdf")
    open(html_path, "w", encoding="utf-8").write(html)

    sys.path.insert(0, BASE)
    from pdf_html import html_a_pdf
    ok, motor = html_a_pdf(html, salida)
    if not ok:
        print("ERROR: ningún motor de PDF disponible (weasyprint/chromium/brave)"); return 1

    print("PDF:", salida, "(motor: " + motor + ")")
    print(f"periodo {a.desde} → {a.hasta} · {len(filas)} predios · {len(cert)} certificables · {len(apl)} aplazados · {len(veredas)} veredas")
    for f in filas:
        print(f"  {f['nombre']:<16} {f['vereda']:<14} {f['primera']} {f['concepto']:<13} F {f['fc']}/{f['ft']} · {f['hall']} hall")
    return 0


if __name__ == "__main__":
    sys.exit(main())
