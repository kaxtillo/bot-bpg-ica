#!/usr/bin/env python3
"""
generar_plan_accion.py — Plan de acción BPG (Res. 067449) para un predio.

Genera un documento HTML imprimible con: datos del predio, calificación real
(leída de la BD), análisis de la brecha, plan de acción por hallazgo
(acción correctiva, responsable, plazo, evidencia) y cronograma por fases.

Uso:
  python3 generar_plan_accion.py "EL ENCANTO" [--salida /ruta/plan.html]
"""
import json, os, sqlite3, sys
from datetime import date, timedelta

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
UMBRALES = {"F": 100, "My": 80, "Mn": 60}
TIPO_NOMBRE = {"F": "Fundamental", "My": "Mayor", "Mn": "Menor"}

# ── Acciones correctivas por criterio (contenido técnico BPG) ──────────────
# accion / responsable / plazo_dias / evidencia
ACCIONES = {
    "1.4": ("Implementar el registro escrito de diagnósticos y mortalidades: formato con fecha, "
            "identificación del animal, signos observados, diagnóstico, tratamiento y desenlace. "
            "Diligenciarlo en cada caso atendido y archivarlo.",
            "Productor + Médico Veterinario", 15,
            "Bitácora de diagnósticos y mortalidades diligenciada (últimos 3 meses)"),
    "2.1": ("Identificar de forma única e individual la totalidad de los animales del hato: "
            "arete/chapeta numerada (o tatuaje) y cotejo contra el inventario. Ningún animal sin "
            "identificación.",
            "Productor", 30,
            "Censo animal 100% identificado + inventario cotejado"),
    "6.8": ("Abrir el registro de tratamientos: formato con fecha, animal, producto aplicado, "
            "lote, dosis, vía de administración, tiempo de retiro y responsable de la aplicación.",
            "Productor + Médico Veterinario", 15,
            "Registro de tratamientos diligenciado y firmado"),
    "1.2": ("Solicitar ante el ICA la certificación oficial vigente que acredite el hato libre de "
            "brucelosis y tuberculosis (pruebas diagnósticas y trámite de certificación). "
            "Mantener la vigencia y el documento archivado en el predio.",
            "Productor + Médico Veterinario (trámite ICA)", 90,
            "Certificado oficial vigente de hato libre de brucelosis y tuberculosis"),
    "2.2": ("Abrir ficha individual por animal: nacimiento, genealogía, identificación, "
            "producción, eventos sanitarios y reproductivos. Integrarla con el sistema de "
            "identificación del criterio 2.1.",
            "Productor", 30,
            "Fichas individuales por animal (o sistema equivalente)"),
    "3.2": ("Implementar el registro escrito de ingreso de personas y vehículos al predio: libro "
            "o formato en el punto de ingreso, con fecha, nombre, procedencia, motivo de la visita "
            "y control de bioseguridad aplicado.",
            "Productor", 15,
            "Registro de visitas diligenciado en el punto de ingreso"),
    "6.10": ("Implementar el control de inventario de productos veterinarios: formato con entradas, "
             "salidas, lote, fecha de vencimiento y saldos; revisión mensual.",
             "Productor", 30,
             "Inventario de productos veterinarios actualizado"),
    "7.7": ("Realizar el monitoreo anual de la calidad del agua para consumo animal: análisis "
            "fisicoquímico y microbiológico en laboratorio y archivo del resultado con las acciones "
            "tomadas si hay desviaciones.",
            "Productor + Médico Veterinario", 60,
            "Resultado de laboratorio del agua (vigencia anual)"),
    "3.5": ("Señalizar cada área de producción en lugar visible: rótulos en bodega, almacén, "
            "botiquín, cuarto de tanque y áreas de manejo.",
            "Productor", 15,
            "Rótulos visibles instalados (registro fotográfico)"),
    "7.6": ("Implementar el inventario de alimentos y materias primas: formato con entradas, "
            "salidas, lote, fecha de vencimiento y saldos; revisión mensual.",
            "Productor", 30,
            "Inventario de alimentos y materias primas actualizado"),
}
GENERICA = ("Documentar y evidenciar el cumplimiento del criterio conforme a la Resolución "
            "067449 (Forma 3-852 V6), con registro escrito y verificable.",
            "Productor", 30, "Registro/evidencia documental del criterio")


def crear_plan(predio, salida=None):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    p = con.execute("SELECT * FROM predios WHERE UPPER(TRIM(nombre))=?",
                    (predio.strip().upper(),)).fetchone()
    if not p:
        print(f"❌ Predio no encontrado: {predio}")
        sys.exit(1)
    a = con.execute("SELECT * FROM auditorias WHERE predio_id=? ORDER BY fecha DESC LIMIT 1",
                    (p["id"],)).fetchone()
    hallazgos = con.execute(
        """SELECT c.id, c.tipo, c.nombre, c.articulo, c.pregunta
           FROM respuestas r JOIN criterios c ON c.id=r.criterio_id
           WHERE r.auditoria_id=? AND r.respuesta='NO'""", (a["id"],)).fetchall()
    orden = {"F": 1, "My": 2, "Mn": 3}
    hallazgos = sorted(hallazgos, key=lambda h: (orden.get(h["tipo"], 9), [int(x) for x in h["id"].split(".")]))

    # estado de seguimiento (si la tabla existe — ver seguimiento.py)
    estados = {}
    try:
        for r in con.execute("SELECT criterio_id, estado FROM seguimiento WHERE auditoria_id=?",
                             (a["id"],)):
            estados[r["criterio_id"]] = r["estado"]
    except sqlite3.OperationalError:
        pass

    datos = {
        "predio": p["nombre"], "propietario": p["propietario"] or "—",
        "identificacion": p["identificacion"] or "—", "telefono": p["telefono"] or "—",
        "municipio": p["municipio"] or "—", "vereda": p["vereda"] or "—",
        "fecha": a["fecha"], "concepto": a["concepto"],
    }
    res = {}
    for t in ("F", "My", "Mn"):
        tot = a[f"{t.lower()}_total"] or 0
        cum = a[f"{t.lower()}_cumplidos"] or 0
        pct = a[f"{t.lower()}_pct"] or 0
        res[t] = {"cumplidos": cum, "total": tot, "pct": pct,
                  "umbral": UMBRALES[t], "ok": pct >= UMBRALES[t]}

    f_faltan = res["F"]["total"] - res["F"]["cumplidos"]
    mn_ok_umbral = UMBRALES["Mn"] / 100 * res["Mn"]["total"]
    import math
    mn_necesarios = max(0, math.ceil(mn_ok_umbral - res["Mn"]["cumplidos"]))
    my_faltan = 0 if res["My"]["ok"] else math.ceil(UMBRALES["My"] / 100 * res["My"]["total"] - res["My"]["cumplidos"])

    # ruta mínima a certificable
    ruta = [h for h in hallazgos if h["tipo"] == "F"]
    mn_no = [h for h in hallazgos if h["tipo"] == "Mn"]
    ruta += mn_no[:mn_necesarios]
    ruta_ids = {h["id"] for h in ruta}

    # fases
    fases = {1: [], 2: [], 3: []}
    for h in hallazgos:
        acc = ACCIONES.get(h["id"], GENERICA)
        dias = acc[2]
        f = 1 if dias <= 15 else (2 if dias <= 40 else 3)
        fases[f].append(h)

    filas = []
    for h in hallazgos:
        accion, resp, plazo, evid = ACCIONES.get(h["id"], GENERICA)
        obligatorio = "Sí" if h["id"] in ruta_ids else "Recomendado"
        filas.append({
            "id": h["id"], "tipo": h["tipo"], "tipo_nombre": TIPO_NOMBRE[h["tipo"]],
            "nombre": h["nombre"], "articulo": h["articulo"] or "—",
            "pregunta": h["pregunta"] or "", "accion": accion, "responsable": resp,
            "plazo": plazo, "limite": (date.today() + timedelta(days=plazo)).isoformat(),
            "evidencia": evid, "obligatorio": obligatorio,
            "estado": estados.get(h["id"], "pendiente"),
        })

    hoy = date.today()
    doc = {
        "datos": datos, "res": res, "filas": filas,
        "total_hallazgos": len(filas),
        "ruta": [{"id": h["id"], "nombre": h["nombre"], "tipo": h["tipo"]} for h in ruta],
        "mn_necesarios": mn_necesarios, "f_faltan": f_faltan, "my_faltan": my_faltan,
        "generado": hoy.isoformat(),
        "progreso": {
            "cerrados": sum(1 for f in filas if f["estado"] == "cerrado"),
            "en_proceso": sum(1 for f in filas if f["estado"] == "en_proceso"),
            "total": len(filas),
            "oblig_total": sum(1 for f in filas if f["obligatorio"] == "Sí"),
            "oblig_cerrados": sum(1 for f in filas if f["obligatorio"] == "Sí" and f["estado"] == "cerrado"),
        },
        "fases": {k: [{"id": h["id"], "nombre": h["nombre"], "tipo": h["tipo"]} for h in v]
                  for k, v in fases.items()},
    }

    html = PLANTILLA.replace("__PLAN__", json.dumps(doc, ensure_ascii=False))
    salida = salida or os.path.join(BASE, f"Plan_Accion_{p['nombre'].replace(' ', '_')}.html")
    open(salida, "w", encoding="utf-8").write(html)
    print(f"OK {salida}")
    print(f"   {datos['predio']} — {datos['concepto']} · F {res['F']['pct']}% / "
          f"My {res['My']['pct']}% / Mn {res['Mn']['pct']}%")
    print(f"   {len(filas)} hallazgos · ruta mínima: {len(ruta)} criterios "
          f"({', '.join(x['id'] for x in doc['ruta'])})")
    return salida


PLANTILLA = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Plan de Acción BPG</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#eef2f0;color:#1c2b26;line-height:1.5}
.hoja{max-width:920px;margin:0 auto;background:#fff;padding:34px 40px 44px;
      box-shadow:0 2px 14px rgba(0,0,0,.09)}
header{border-bottom:3px solid #0B3D2E;padding-bottom:14px;margin-bottom:20px}
h1{font-size:22px;color:#0B3D2E}
.sub{font-size:12.5px;color:#5c6f68;margin-top:3px}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px 18px;margin:16px 0 20px}
.meta div{font-size:12.5px}
.meta b{color:#0B3D2E}
.veredicto{background:#fdeaea;border-left:5px solid #C62828;padding:12px 16px;border-radius:6px;margin-bottom:18px}
.veredicto.ok{background:#eaf5ec;border-color:#2E7D32}
.veredicto h2{font-size:16px;margin-bottom:4px}
.veredicto p{font-size:12.5px}
.cifras{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:22px}
.cif{background:#f7faf8;border:1px solid #dfe7e3;border-radius:8px;padding:11px 13px}
.cif .t{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#6b7c76}
.cif .v{font-size:20px;font-weight:700;margin-top:2px}
.cif .u{font-size:11.5px;color:#6b7c76}
.no{color:#C62828}.si{color:#2E7D32}
h3{font-size:15px;color:#0B3D2E;margin:22px 0 9px;padding-bottom:5px;border-bottom:1px solid #e3e9e6}
.ruta{background:#fff8e6;border-left:4px solid #E65100;padding:11px 15px;border-radius:6px;font-size:12.5px;margin-bottom:6px}
.ruta ul{margin:6px 0 0 18px}
.acc{border:1px solid #dfe7e3;border-left-width:4px;border-radius:7px;padding:12px 14px;margin-bottom:11px;
     break-inside:avoid;page-break-inside:avoid}
.acc.F{border-left-color:#C62828}.acc.My{border-left-color:#E65100}.acc.Mn{border-left-color:#F9A825}
.acc .cab{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:baseline}
.acc .id{font-weight:700;font-size:14px;color:#0B3D2E}
.tag{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;
     padding:2px 8px;border-radius:11px;color:#fff}
.tag.F{background:#C62828}.tag.My{background:#E65100}.tag.Mn{background:#F9A825}
.tag.obl{background:#0B3D2E}.tag.rec{background:#7d8b86}
.est{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;
     padding:2px 8px;border-radius:11px;border:1px solid;margin-left:4px}
.est.pendiente{color:#8a6d00;border-color:#e0c060;background:#fff8e1}
.est.en_proceso{color:#0d5c8c;border-color:#8fc2e0;background:#e8f4fb}
.est.cerrado{color:#1b5e20;border-color:#9ccc9f;background:#e8f5e9}
.avance{background:#f2f7f4;border:1px solid #dfe7e3;border-radius:8px;padding:12px 15px;
        margin-bottom:18px;font-size:12.5px}
.avance .bar{height:9px;background:#e0e7e3;border-radius:5px;overflow:hidden;margin-top:8px}
.avance .bar i{display:block;height:100%;background:#2E7D32}
.acc.cerrado{opacity:.62}
.preg{font-size:12px;color:#5c6f68;font-style:italic;margin:6px 0}
.hacer{font-size:12.5px;margin:6px 0}
.hacer b{color:#0B3D2E}
.pie{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:7px 16px;
     margin-top:9px;padding-top:8px;border-top:1px dashed #dfe7e3;font-size:11.5px;color:#4a5b55}
.pie b{color:#0B3D2E}
.fases{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.fase{background:#f7faf8;border:1px solid #dfe7e3;border-radius:8px;padding:11px 13px;font-size:12px}
.fase h4{font-size:12.5px;color:#0B3D2E;margin-bottom:6px}
.fase ul{margin-left:16px}
footer{margin-top:26px;padding-top:12px;border-top:1px solid #e3e9e6;font-size:11px;color:#7d8b86}
@media print{body{background:#fff}.hoja{box-shadow:none;padding:0}.acc,.fase{break-inside:avoid}}
@media(max-width:760px){.cifras,.fases{grid-template-columns:1fr}.hoja{padding:20px}}
</style></head><body><div class="hoja">
<header><h1>Plan de Acción — Buenas Prácticas Ganaderas</h1>
<div class="sub">Resolución ICA 067449 · Forma 3-852 V6 · Preparación para certificación de predio</div></header>
<div id="meta"></div><div id="veredicto"></div><div id="avance"></div><div id="cifras"></div>
<h3>Ruta mínima para alcanzar la certificación</h3><div id="ruta"></div>
<h3>Plan de acción por hallazgo</h3><div id="acciones"></div>
<h3>Cronograma por fases</h3><div class="fases" id="fases"></div>
<footer id="pie"></footer>
</div>
<script>
const P=__PLAN__;
const e=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const d=P.datos, r=P.res;
document.getElementById('meta').innerHTML=`
 <div><b>Predio:</b> ${e(d.predio)}</div>
 <div><b>Propietario:</b> ${e(d.propietario)}</div>
 <div><b>Identificación:</b> ${e(d.identificacion)}</div>
 <div><b>Teléfono:</b> ${e(d.telefono)}</div>
 <div><b>Municipio:</b> ${e(d.municipio)} · <b>Vereda:</b> ${e(d.vereda)}</div>
 <div><b>Fecha de auditoría:</b> ${e(d.fecha)}</div>`;
const ok=d.concepto.toLowerCase().indexOf('certificable')>=0;
document.getElementById('veredicto').innerHTML=
 `<div class="veredicto ${ok?'ok':''}"><h2>Concepto: ${e(d.concepto)}</h2>
  <p>${ok?'El predio cumple los umbrales. Se recomienda cerrar los hallazgos restantes para sostener la condición.'
        :'El predio no alcanza los umbrales exigidos. Los criterios Fundamentales deben cumplirse al 100%; los Mayores ≥80% y los Menores ≥60% (los NA no cuentan).'}</p></div>`;
const pg=P.progreso||{cerrados:0,en_proceso:0,total:0,oblig_total:0,oblig_cerrados:0};
const pct=pg.total?Math.round(100*pg.cerrados/pg.total):0;
document.getElementById('avance').innerHTML=
 `<div class="avance"><b>Avance del plan:</b> ${pg.cerrados} de ${pg.total} hallazgo(s) cerrados (${pct}%)
  · ${pg.en_proceso} en proceso
  · <b>Obligatorios para certificar: ${pg.oblig_cerrados}/${pg.oblig_total}</b>
  <div class="bar"><i style="width:${pct}%"></i></div></div>`;
const c=(t,n)=>{const m=r[t];return `<div class="cif"><div class="t">${n}</div>
 <div class="v ${m.ok?'si':'no'}">${m.pct}%</div>
 <div class="u">${m.cumplidos}/${m.total} · umbral ${m.umbral}% ${m.ok?'✓ cumple':'✗ no cumple'}</div></div>`};
document.getElementById('cifras').innerHTML=c('F','Fundamentales (F)')+c('My','Mayores (My)')+c('Mn','Menores (Mn)');
const ruta=(P.ruta||[]);
document.getElementById('ruta').innerHTML= ruta.length
 ? `<div class="ruta">Cumpliendo estos <b>${ruta.length}</b> criterios el predio alcanza la calificación de <b>Certificable</b>:<ul>${ruta.map(x=>`<li><b>${e(x.id)}</b> ${e(x.nombre)} <i>(${e(x.tipo)})</i></li>`).join('')}</ul>
    <div style="margin-top:6px">Se requiere cerrar los <b>${P.f_faltan}</b> criterios Fundamentales pendientes${P.mn_necesarios>0?` y <b>${P.mn_necesarios}</b> Menor(es) para superar el 60%`:''}${P.my_faltan>0?` y <b>${P.my_faltan}</b> Mayor(es) para superar el 80%`:' (los Mayores ya cumplen)'}.</div></div>`
 : `<div class="ruta">El predio no presenta hallazgos en la última auditoría.</div>`;
document.getElementById('acciones').innerHTML=P.filas.map(f=>`
 <div class="acc ${f.tipo} ${f.estado==='cerrado'?'cerrado':''}">
  <div class="cab"><span class="id">${e(f.id)} ${e(f.nombre)}</span>
   <span><span class="tag ${f.tipo}">${e(f.tipo_nombre)}</span>
   <span class="tag ${f.obligatorio==='Sí'?'obl':'rec'}">${e(f.obligatorio)}</span>
   <span class="est ${e(f.estado)}">${e(String(f.estado).replace('_',' '))}</span></span></div>
  <div class="preg">Art. ${e(f.articulo)} — ${e(f.pregunta)}</div>
  <div class="hacer"><b>Acción correctiva:</b> ${e(f.accion)}</div>
  <div class="pie"><div><b>Responsable:</b> ${e(f.responsable)}</div>
   <div><b>Plazo:</b> ${f.plazo} días (hasta ${e(f.limite)})</div>
   <div><b>Evidencia de verificación:</b> ${e(f.evidencia)}</div></div>
 </div>`).join('');
const F=P.fases, nm={1:'Fase 1 — Inmediata (≤15 días)',2:'Fase 2 — Corto plazo (16-40 días)',3:'Fase 3 — Mediano plazo (>40 días)'};
document.getElementById('fases').innerHTML=[1,2,3].map(k=>{
 const l=F[k]||[];
 return `<div class="fase"><h4>${nm[k]}</h4>${l.length?`<ul>${l.map(x=>`<li><b>${e(x.id)}</b> ${e(x.nombre)} <i>(${e(x.tipo)})</i></li>`).join('')}</ul>`:'<div style="color:#7d8b86">Sin hallazgos.</div>'}</div>`;
}).join('');
document.getElementById('pie').innerHTML=`Documento de preparación para la certificación en Buenas Prácticas Ganaderas (Res. ICA 067449). Generado el ${e(P.generado)} a partir de la auditoría del ${e(d.fecha)} — ${P.total_hallazgos} hallazgo(s). No constituye certificación oficial del ICA.`;
</script></body></html>"""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    salida = None
    if "--salida" in sys.argv:
        salida = sys.argv[sys.argv.index("--salida") + 1]
    crear_plan(sys.argv[1], salida)
