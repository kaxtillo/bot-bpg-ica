#!/usr/bin/env python3
"""generar_dashboard.py — Dashboard HTML reactivo con mapa + filtro por municipio."""
import json, os, sqlite3

BASE = os.path.expanduser("~/auditorias_bpg")
OUT = os.path.join(BASE, "Dashboard_Auditorias_BPG_ICA.html")

con = sqlite3.connect(os.path.join(BASE, "auditorias_bpg.db"))
con.row_factory = sqlite3.Row
rows = con.execute("""
SELECT p.nombre, p.municipio, p.vereda, p.propietario, p.latitud lat, p.longitud lon,
       a.fecha, a.concepto, a.f_pct, a.my_pct, a.mn_pct,
       (SELECT COUNT(*) FROM respuestas r WHERE r.auditoria_id=a.id AND r.respuesta='NO') hallazgos
FROM predios p
JOIN (SELECT predio_id, MAX(id) mid FROM auditorias GROUP BY predio_id) l ON l.predio_id=p.id
JOIN auditorias a ON a.id=l.mid
WHERE p.latitud IS NOT NULL AND p.latitud!=0
ORDER BY p.nombre""").fetchall()
datos = [dict(r) for r in rows]
total = len(datos)
munis = sorted(set(d["municipio"] for d in datos))

html = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard Auditorías BPG ICA</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root{--v:#0B3D2E;--g:#2E7D32;--r:#C62828}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#f4f7f5;color:#1c2b26}
header{background:var(--v);color:#fff;padding:18px 30px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
header h1{font-size:20px} header p{opacity:.85;font-size:12.5px;margin-top:2px}
.filtro{background:#fff;color:#0B3D2E;border:none;border-radius:8px;padding:9px 14px;font-size:14px;font-weight:600;cursor:pointer;min-width:150px}
.wrap{padding:18px 30px;max-width:1250px;margin:0 auto}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:18px}
.card{background:#fff;border-radius:12px;padding:15px;box-shadow:0 2px 6px rgba(0,0,0,.06)}
.card .num{font-size:26px;font-weight:700;margin-top:3px}
.card .lab{font-size:11px;color:#6b7c76;text-transform:uppercase;letter-spacing:.5px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.plt{background:#fff;border-radius:12px;padding:14px;box-shadow:0 2px 6px rgba(0,0,0,.06)}
.plt h3{font-size:14px;color:var(--v);margin-bottom:8px}
#mapa{height:400px;border-radius:10px;z-index:0}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{background:var(--v);color:#fff;padding:7px 5px;text-align:left;position:sticky;top:0}
td{padding:6px 5px;border-bottom:1px solid #e3e9e6}
.badge{padding:2px 7px;border-radius:12px;color:#fff;font-size:11px;font-weight:600}
.cert{background:var(--g)} .apl{background:var(--r)}
.full{grid-column:1/-1}
.scroll{max-height:380px;overflow:auto;border-radius:8px}
#resumenFiltro{font-size:12px;color:#6b7c76;margin-bottom:8px}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
</style></head><body>
<header><div><h1>📊 Dashboard Auditorías BPG ICA</h1>
<p>Resolución 067449 · Forma 3-852 V6 · <span id="ttlPredios">0</span> predios</p></div>
<div><label style="font-size:12px;opacity:.8;margin-right:6px">Municipio:</label><select id="selMun" class="filtro"></select></div></header>
<div class="wrap">
 <div class="cards">
  <div class="card"><div class="lab">Predios</div><div class="num" id="kPredios">0</div></div>
  <div class="card"><div class="lab" style="color:var(--g)">Certificables</div><div class="num" style="color:var(--g)" id="kCert">0</div></div>
  <div class="card"><div class="lab" style="color:var(--r)">Aplazados</div><div class="num" style="color:var(--r)" id="kApl">0</div></div>
 </div>
 <div class="plt" style="margin-bottom:18px"><h3>🗺️ Mapa de predios (ubicación y certificación)</h3><div id="mapa"></div></div>
 <div class="grid">
  <div class="plt"><h3>Estado de certificación</h3><canvas id="cConcepto" height="160"></canvas></div>
  <div class="plt"><h3>Predios por municipio <span style="font-size:11px;color:#6b7c76;font-weight:400">(clic en barra para filtrar)</span></h3><canvas id="cMunicipio" height="160"></canvas></div>
  <div class="plt full"><h3>Detalle de predios</h3><div id="resumenFiltro"></div>
   <div class="scroll"><table><thead><tr><th>Predio</th><th>Municipio</th><th>Concepto</th><th>F%</th><th>My%</th><th>Mn%</th><th>Hallazgos</th></tr></thead>
   <tbody id="tabla"></tbody></table></div>
  </div>
 </div>
</div>
<script>
const TODOS=__DATOS__;
let MUN='Todos';
const munis=[...new Set(TODOS.map(d=>d.municipio))].sort();
const map=L.map('mapa').setView([2.43,-76.55],9);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(map);
const iconV=L.divIcon({className:'',html:'<div style="width:14px;height:14px;border-radius:50%;background:#2E7D32;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,.5)"></div>'});
const iconR=L.divIcon({className:'',html:'<div style="width:14px;height:14px;border-radius:50%;background:#C62828;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,.5)"></div>'});
let capaPredios=null, chConc=null, chMun=null;
function renderMapa(ds){
  if(capaPredios)map.removeLayer(capaPredios);
  const feats=ds.map(d=>({type:'Feature',properties:d,geometry:{type:'Point',coordinates:[d.lon,d.lat]}}));
  capaPredios=L.geoJSON({type:'FeatureCollection',features:feats},{
    pointToLayer:function(f,ll){return L.marker(ll,{icon:f.properties.concepto==='Certificable'?iconV:iconR})},
    onEachFeature:function(f,l){l.bindPopup('<b>'+f.properties.nombre+'</b> · '+f.properties.municipio+'<br>'+f.properties.concepto+' ('+f.properties.fecha+')<br>F '+f.properties.f_pct+'% · My '+f.properties.my_pct+'% · Mn '+f.properties.mn_pct+'%')}}).addTo(map);
  if(feats.length){const b=L.geoJSON({type:'FeatureCollection',features:feats}).getBounds();if(b.isValid())map.fitBounds(b.pad(0.25));}
  else{map.setView([2.43,-76.55],9);}
}
function renderConc(ds){
  const c={Certificable:0,Aplazado:0};
  ds.forEach(d=>{if(c[d.concepto]!==undefined)c[d.concepto]++;});
  const labels=['Certificable','Aplazado'].filter(k=>c[k]>0), vals=labels.map(k=>c[k]);
  if(chConc)chConc.destroy();
  chConc=new Chart(cConcepto,{type:'doughnut',data:{labels:labels,datasets:[{data:vals,backgroundColor:['#2E7D32','#C62828']}]},options:{plugins:{legend:{position:'bottom'}}}});
}
function renderMun(){
  const c={};TODOS.forEach(d=>c[d.municipio]=(c[d.municipio]||0)+1);
  const labels=Object.keys(c).sort(), vals=labels.map(k=>c[k]);
  if(chMun)chMun.destroy();
  chMun=new Chart(cMunicipio,{type:'bar',
    data:{labels:labels,datasets:[{label:'Predios',data:vals,backgroundColor:labels.map(l=>l===MUN?'#E65100':'#0B3D2E')}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:function(x){return x.parsed.y+' predios'}}}},
      onClick:function(e,el){if(el.length){MUN=labels[el[0].index];document.getElementById('selMun').value=MUN;actualizar();}}}});
}
function renderKpis(ds){
  const c=ds.filter(d=>d.concepto==='Certificable').length;
  document.getElementById('kPredios').textContent=ds.length;
  document.getElementById('kCert').textContent=c;
  document.getElementById('kApl').textContent=ds.length-c;
  document.getElementById('ttlPredios').textContent=ds.length;
  document.getElementById('resumenFiltro').textContent=MUN==='Todos'?('Mostrando los '+ds.length+' predios'):('Focalizado en '+MUN+' — '+ds.length+' predios');
}
function renderTabla(ds){
  document.getElementById('tabla').innerHTML=ds.map(d=>'<tr><td>'+d.nombre+'</td><td>'+d.municipio+'</td><td><span class="badge '+(d.concepto==='Certificable'?'cert':'apl')+'">'+d.concepto+'</span></td><td>'+Math.round(d.f_pct)+'%</td><td>'+Math.round(d.my_pct)+'%</td><td>'+Math.round(d.mn_pct)+'%</td><td>'+d.hallazgos+'</td></tr>').join('');
}
function actualizar(){
  const ds=MUN==='Todos'?TODOS:TODOS.filter(d=>d.municipio===MUN);
  renderKpis(ds);renderMapa(ds);renderConc(ds);renderMun();renderTabla(ds);
}
const sel=document.getElementById('selMun');
['Todos'].concat(munis).forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent=m;sel.appendChild(o)});
sel.value=MUN;
sel.addEventListener('change',function(){MUN=sel.value;actualizar()});
actualizar();
</script></body></html>"""

# insertar datos (placeholder en string normal, sin conflicto con llaves JS)
html = html.replace("__DATOS__", json.dumps(datos, ensure_ascii=False))
open(OUT, "w", encoding="utf-8").write(html)
print(f"OK {OUT} ({total} predios, municipios: {munis})")