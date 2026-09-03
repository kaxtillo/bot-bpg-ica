#!/usr/bin/env python3
"""generar_dashboard.py — Regenera el dashboard HTML con mapa a partir de la BD.
Llámado desde sincronizar_todo.sh cuando los datos cambian."""
import json, os, sqlite3

BASE = os.path.expanduser("~/auditorias_bpg")
OUT = os.path.join(BASE, "Dashboard_Auditorias_BPG_ICA.html")

con = sqlite3.connect(os.path.join(BASE, "auditorias_bpg.db"))
con.row_factory = sqlite3.Row
rows = con.execute("""
SELECT p.nombre, p.municipio, p.vereda, p.propietario, p.latitud lat, p.longitud lon,
       a.fecha, a.concepto, a.f_pct, a.my_pct, a.mn_pct, a.observaciones,
       (SELECT COUNT(*) FROM respuestas r WHERE r.auditoria_id=a.id AND r.respuesta='NO') hallazgos
FROM predios p
JOIN (SELECT predio_id, MAX(id) mid FROM auditorias GROUP BY predio_id) l ON l.predio_id=p.id
JOIN auditorias a ON a.id=l.mid
WHERE p.latitud IS NOT NULL AND p.latitud!=0
ORDER BY p.nombre""").fetchall()
datos = [dict(r) for r in rows]
json_datos = json.dumps(datos, ensure_ascii=False)

features = []
for d in datos:
    color = "#2E7D32" if d["concepto"] == "Certificable" else "#C62828"
    features.append({"type": "Feature", "properties": {"nombre": d["nombre"],
        "concepto": d["concepto"], "municipio": d["municipio"], "fecha": d["fecha"],
        "f": f"{d['f_pct']:.0f}%", "my": f"{d['my_pct']:.0f}%", "mn": f"{d['mn_pct']:.0f}%",
        "obs": (d["observaciones"] or "")[:200], "marker-color": color},
        "geometry": {"type": "Point", "coordinates": [d["lon"], d["lat"]]}})
geojson = {"type": "FeatureCollection", "features": features}
json_geo = json.dumps(geojson, ensure_ascii=False)

total = len(datos); cert = sum(1 for d in datos if d["concepto"]=="Certificable")
apl = total-cert
prom_f = sum(d["f_pct"] for d in datos)/total if total else 0

html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard Auditorías BPG ICA</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root{{--v:#0B3D2E;--g:#2E7D32;--r:#C62828}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f4f7f5;color:#1c2b26}}
header{{background:var(--v);color:#fff;padding:20px 30px}}
header h1{{font-size:21px}} header p{{opacity:.85;font-size:13px;margin-top:3px}}
.wrap{{padding:20px 30px;max-width:1250px;margin:0 auto}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:20px}}
.card{{background:#fff;border-radius:12px;padding:15px;box-shadow:0 2px 6px rgba(0,0,0,.06)}}
.card .num{{font-size:26px;font-weight:700;margin-top:3px}}
.card .lab{{font-size:11px;color:#6b7c76;text-transform:uppercase;letter-spacing:.5px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.plt{{background:#fff;border-radius:12px;padding:14px;box-shadow:0 2px 6px rgba(0,0,0,.06)}}
.plt h3{{font-size:14px;color:var(--v);margin-bottom:8px}}
#mapa{{height:420px;border-radius:10px;z-index:0}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
th{{background:var(--v);color:#fff;padding:7px 5px;text-align:left}}
td{{padding:6px 5px;border-bottom:1px solid #e3e9e6}}
.badge{{padding:2px 7px;border-radius:12px;color:#fff;font-size:11px;font-weight:600}}
.cert{{background:var(--g)}} .apl{{background:var(--r)}}
.full{{grid-column:1/-1}}
.leaflet-container{{font-family:inherit}}
@media(max-width:820px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header><h1>📊 Dashboard Auditorías BPG ICA</h1>
<p>Resolución 067449 · Forma 3-852 V6 · {total} predios georreferenciados</p></header>
<div class="wrap">
 <div class="cards">
  <div class="card"><div class="lab">Predios</div><div class="num">{total}</div></div>
  <div class="card"><div class="lab" style="color:var(--g)">Certificables</div><div class="num" style="color:var(--g)">{cert}</div></div>
  <div class="card"><div class="lab" style="color:var(--r)">Aplazados</div><div class="num" style="color:var(--r)">{apl}</div></div>
  <div class="card"><div class="lab">% F promedio</div><div class="num">{prom_f:.1f}%</div></div>
 </div>
 <div class="plt" style="margin-bottom:18px"><h3>🗺️ Mapa de predios (ubicación y certificación)</h3><div id="mapa"></div></div>
 <div class="grid">
  <div class="plt"><h3>Estado de certificación</h3><canvas id="cConcepto" height="150"></canvas></div>
  <div class="plt"><h3>Predios por municipio</h3><canvas id="cMunicipio" height="150"></canvas></div>
  <div class="plt"><h3>Hallazgos por predio (top)</h3><canvas id="cHallazgos" height="220"></canvas></div>
  <div class="plt"><h3>Cumplimiento F/My/Mn</h3><canvas id="cFmy" height="220"></canvas></div>
  <div class="plt full"><h3>Detalle de predios</h3>
   <table><thead><tr><th>Predio</th><th>Municipio</th><th>Concepto</th><th>F%</th><th>My%</th><th>Mn%</th><th>Hallazgos</th></tr></thead>
   <tbody>{"".join(f'<tr><td>{d["nombre"]}</td><td>{d["municipio"]}</td><td><span class="badge {"cert" if d["concepto"]=="Certificable" else "apl"}">{d["concepto"]}</span></td><td>{d["f_pct"]:.0f}%</td><td>{d["my_pct"]:.0f}%</td><td>{d["mn_pct"]:.0f}%</td><td>{d["hallazgos"]}</td></tr>' for d in datos)}</tbody></table>
  </div>
 </div>
</div>
<script>
const D={json_datos};
const geo={json_geo};
const map=L.map('mapa').setView([2.43,-76.55],9);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{attribution:'© OpenStreetMap'}}).addTo(map);
const iconV=L.divIcon({{className:'',html:'<div style="width:14px;height:14px;border-radius:50%;background:#2E7D32;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,.5)"></div>'}});
const iconR=L.divIcon({{className:'',html:'<div style="width:14px;height:14px;border-radius:50%;background:#C62828;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,.5)"></div>'}});
L.geoJSON(geo,{{pointToLayer:function(f,latlng){{return L.marker(latlng,{{icon:f.properties.concepto==='Certificable'?iconV:iconR}})}},
 onEachFeature:function(f,l){{l.bindPopup('<b>'+f.properties.nombre+'</b> · '+f.properties.municipio+'<br>'+f.properties.concepto+' ('+f.properties.fecha+')<br>F '+f.properties.f+' · My '+f.properties.my+' · Mn '+f.properties.mn+(f.properties.obs?'<br><i>'+f.properties.obs+'</i>':''))}} }}).addTo(map);
map.fitBounds(L.geoJSON(geo).getBounds().pad(0.1));
function agrupar(a,fn){{const m={{}};a.forEach(x=>{{const k=fn(x);m[k]=(m[k]||0)+1}});return m}}
const conc=agrupar(D,d=>d.concepto), mun=agrupar(D,d=>d.municipio);
new Chart(cConcepto,{{type:'doughnut',data:{{labels:Object.keys(conc),datasets:[{{data:Object.values(conc),backgroundColor:['#2E7D32','#C62828']}}]}},options:{{plugins:{{legend:{{position:'bottom'}}}}}}}});
new Chart(cMunicipio,{{type:'bar',data:{{labels:Object.keys(mun),datasets:[{{label:'Predios',data:Object.values(mun),backgroundColor:'#0B3D2E'}}]}},options:{{plugins:{{legend:{{display:false}}}}}}}});
const hs=[...D].sort((a,b)=>b.hallazgos-a.hallazgos).slice(0,10);
new Chart(cHallazgos,{{type:'bar',data:{{labels:hs.map(d=>d.nombre),datasets:[{{label:'Hallazgos',data:hs.map(d=>d.hallazgos),backgroundColor:'#E65100'}}]}},options:{{indexAxis:'y',plugins:{{legend:{{display:false}}}}}}}});
const orden=[...D].sort((a,b)=>a.f_pct-b.f_pct).slice(0,12);
new Chart(cFmy,{{type:'bar',data:{{labels:orden.map(d=>d.nombre),datasets:[{{label:'F',data:orden.map(d=>d.f_pct),backgroundColor:'#0B3D2E'}},{{label:'My',data:orden.map(d=>d.my_pct),backgroundColor:'#2E7D32'}},{{label:'Mn',data:orden.map(d=>d.mn_pct),backgroundColor:'#C9A227'}}]}},options:{{plugins:{{legend:{{position:'bottom'}}}}}}}});
</script></body></html>"""

open(OUT, "w", encoding="utf-8").write(html)
print(f"OK {OUT} ({total} predios)")