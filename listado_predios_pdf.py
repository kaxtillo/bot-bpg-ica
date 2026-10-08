#!/usr/bin/env python3
"""
listado_predios_pdf.py — Listado de predios en PDF (A4) para imprimir o entregar.

Uso:
    listado_predios_pdf.py --municipio "Sotará" [--salida ruta.pdf] [--contacto] [--todos]

- Por defecto incluye SOLO el nombre del propietario (documento de trabajo).
- Con --contacto añade identificación y teléfono (contiene datos personales: no publicar).
- Genera el PDF con chromium headless (Brave falla en esta máquina por el sandbox).
"""
import argparse, datetime, os, sqlite3, subprocess, sys, unicodedata

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
SCRATCH = os.path.expanduser("~/.hermes/cache/scratch")


def sin_tildes(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def predios(municipio):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    filas = con.execute("""
        SELECT p.nombre, p.propietario, p.identificacion, p.telefono, p.municipio, p.vereda,
               a.fecha, a.concepto, a.f_cumplidos, a.f_total, a.my_pct, a.mn_pct,
               (SELECT COUNT(*) FROM respuestas r WHERE r.auditoria_id=a.id AND r.respuesta='NO') h
        FROM predios p
        JOIN auditorias a ON a.id=(SELECT id FROM auditorias WHERE predio_id=p.id
                                   ORDER BY fecha DESC, id DESC LIMIT 1)
        ORDER BY p.vereda, p.nombre""").fetchall()
    if municipio:
        filas = [f for f in filas if sin_tildes(f["municipio"]) == sin_tildes(municipio)]
    return [dict(f) for f in filas]


CSS = """<style>
@page{size:A4 portrait;margin:12mm}
*{box-sizing:border-box}
body{font-family:'Segoe UI',Arial,sans-serif;color:#152a23;margin:0;font-size:10.5px}
h1{font-size:15px;color:#0B3D2E;margin:0 0 2px}
.sub{font-size:10px;color:#555;border-bottom:2px solid #0B3D2E;padding-bottom:5px;margin-bottom:8px}
.resumen{background:#eef3f0;border:1px solid #c9d6d1;border-radius:4px;padding:6px 8px;margin-bottom:8px;font-size:10.5px}
table{width:100%;border-collapse:collapse}
th,td{border:1px solid #b9c4bf;padding:3px 5px;text-align:left;vertical-align:top}
th{background:#0B3D2E;color:#fff;font-size:9.5px;text-transform:uppercase}
td.n{text-align:right;white-space:nowrap}
td.c{text-align:center;white-space:nowrap}
tr:nth-child(even) td{background:#f7faf8}
.cert{color:#2E7D32;font-weight:600}
.apl{color:#C62828;font-weight:600}
.pie{margin-top:10px;border-top:1px solid #ccc;padding-top:6px;font-size:9px;color:#666}
.firma{margin-top:18px;display:flex;gap:40px;font-size:9.5px}
.firma div{flex:1;border-top:1px solid #333;padding-top:3px}
.aviso{background:#FFF3E0;border:1px solid #E65100;color:#8a4b00;border-radius:4px;padding:5px 8px;font-size:9.5px;margin-top:8px}
</style>
"""


def construir_html(datos, municipio, con_contacto):
    hoy = datetime.date.today().strftime("%d/%m/%Y")
    cert = sum(1 for d in datos if (d["concepto"] or "") == "Certificable")
    apl = len(datos) - cert
    veredas = sorted({(d["vereda"] or "—") for d in datos})
    titulo = municipio if municipio else "todos los municipios"

    cabeceras = ["#", "Predio", "Propietario"]
    if con_contacto:
        cabeceras += ["Identificación", "Teléfono"]
    cabeceras += ["Vereda", "Concepto", "F%", "My%", "Mn%", "Hallazgos"]

    filas = []
    for i, d in enumerate(datos, 1):
        celdas = ['<td class="c">' + str(i) + '</td>',
                  "<td><b>" + (d["nombre"] or "") + "</b></td>",
                  "<td>" + (d["propietario"] or "—") + "</td>"]
        if con_contacto:
            celdas += ["<td>" + (d["identificacion"] or "—") + "</td>",
                       "<td>" + (d["telefono"] or "—") + "</td>"]
        clase = "cert" if (d["concepto"] or "") == "Certificable" else "apl"
        celdas += ["<td>" + (d["vereda"] or "—") + "</td>",
                   '<td class="' + clase + '">' + (d["concepto"] or "") + "</td>",
                   '<td class="n">' + str(round(d["f_cumplidos"] * 100.0 / d["f_total"], 1) if d["f_total"] else 0) + "%</td>",
                   '<td class="n">' + str(round(d["my_pct"] or 0, 1)) + "%</td>",
                   '<td class="n">' + str(round(d["mn_pct"] or 0, 1)) + "%</td>",
                   '<td class="c">' + str(d["h"]) + "</td>"]
        filas.append("<tr>" + "".join(celdas) + "</tr>")

    aviso = ""
    if con_contacto:
        aviso = ('<div class="aviso"><b>DOCUMENTO PRIVADO.</b> Contiene identificación y teléfono '
                 'de los productores. No publicar ni compartir: úsalo sólo para el trabajo de campo.</div>')

    return ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
            "<title>Listado BPG - " + titulo + "</title>" + CSS + "</head><body>"
            "<h1>LISTADO DE PREDIOS AUDITADOS — BUENAS PRÁCTICAS GANADERAS</h1>"
            "<div class='sub'>Resolución ICA 067449 · Forma 3-852 V6 · Municipio de " + titulo +
            " · Generado el " + hoy + "</div>"
            "<div class='resumen'><b>" + str(len(datos)) + " predios</b> · " + str(cert) +
            " certificables · " + str(apl) + " aplazados · veredas: " + ", ".join(veredas) + "</div>"
            "<table><thead><tr>" + "".join("<th>" + c + "</th>" for c in cabeceras) +
            "</tr></thead><tbody>" + "".join(filas) + "</tbody></table>"
            + aviso +
            "<div class='firma'><div>Auditor / asesor BPG</div><div>Fecha</div></div>"
            "<div class='pie'>Fuente: base de datos de auditorías BPG ICA (auditoría más reciente de cada "
            "predio). Criterios aplicables según la categoría F / My / Mn · umbrales 100% / 80% / 60% "
            "(los NA no cuentan). Documento de trabajo del asesor; no constituye certificación oficial del ICA.</div>"
            "</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--municipio", default="Sotará")
    ap.add_argument("--todos", action="store_true", help="todos los municipios")
    ap.add_argument("--contacto", action="store_true", help="incluir identificación y teléfono")
    ap.add_argument("--salida", default=None)
    a = ap.parse_args()

    mun = None if a.todos else a.municipio
    datos = predios(mun)
    if not datos:
        print("Sin predios para ese municipio."); return 1

    os.makedirs(SCRATCH, exist_ok=True)
    etiqueta = sin_tildes(mun or "todos").replace(" ", "_")
    html_path = os.path.join(SCRATCH, "listado_" + etiqueta + ".html")
    salida = a.salida or os.path.join(BASE, "Listado_Predios_" + etiqueta.title() + ".pdf")
    open(html_path, "w", encoding="utf-8").write(construir_html(datos, mun, a.contacto))

    perfil = os.path.join(SCRATCH, "cr-listado")
    cmd = ["chromium", "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run",
           "--disable-extensions", "--user-data-dir=" + perfil, "--no-pdf-header-footer",
           "--virtual-time-budget=5000", "--print-to-pdf=" + salida, "file://" + html_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
    if not os.path.exists(salida):
        print("ERROR al generar el PDF:", r.stderr[-300:]); return 1

    print("PDF: " + salida)
    print("predios: " + str(len(datos)) + " · " + (mun or "todos") +
          (" · CON contacto" if a.contacto else " · sin contacto"))
    for d in datos:
        print("  " + (d["nombre"] or "")[:28].ljust(28) + " | " + (d["propietario"] or "—")[:26].ljust(26) +
              " | " + (d["vereda"] or "—")[:16].ljust(16) + " | " + (d["concepto"] or ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
