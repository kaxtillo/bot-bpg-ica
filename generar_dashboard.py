#!/usr/bin/env python3
"""
generar_dashboard.py — Dashboard HTML de auditorías BPG ICA.

Incluye:
  - KPIs (Predios / Certificables / Aplazados) con **filtro por municipio**
    que enfoca todo el tablero (mapa, gráficos, tabla).
  - Mapa Leaflet con marcadores por concepto.
  - **Consulta por número de identificación** (o nombre del predio): muestra la
    ficha del predio con su calificación (F/My/Mn + concepto) y el **estado de
    seguimiento de cada hallazgo** (pendiente / en proceso / cerrado) + avance.

PRIVACIDAD: el propietario, la identificación y el teléfono NO se publican.
La cédula tampoco viaja al HTML: sólo su huella SHA-256 (`cid`), que es con lo que
compara el buscador. Ocultar los campos sólo en el HTML no serviría de nada, porque
los datos irían dentro del `FICHAS` del propio archivo (se leerían con Ctrl+U).
"""
import hashlib, json, os, re, sqlite3, unicodedata

BASE = os.path.expanduser("~/auditorias_bpg")
OUT = os.path.join(BASE, "Dashboard_Auditorias_BPG_ICA.html")
DB = os.path.join(BASE, "auditorias_bpg.db")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row


def _norm_mun(s):
    """Municipio normalizado para agrupar: sin tildes y en minúsculas."""
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def _unificar_municipios(*listas):
    """Unifica variantes del mismo municipio ('CAJIBÍO' vs 'Cajibío').

    La hoja de Google puede traer el municipio en mayúsculas y la BD en formato
    normal, lo que duplicaba la opción en el filtro del tablero (y partía los
    conteos en dos). Se adopta la grafía más frecuente; en empate, la que no
    esté toda en mayúsculas. Modifica los dicts in situ.
    """
    from collections import Counter
    filas = [f for l in listas for f in l]
    grupos = {}
    for f in filas:
        if f.get("municipio"):
            grupos.setdefault(_norm_mun(f["municipio"]), []).append(f["municipio"])
    canon = {k: max(Counter(v).items(), key=lambda kv: (kv[1], not kv[0].isupper()))[0]
             for k, v in grupos.items()}
    for f in filas:
        if f.get("municipio"):
            f["municipio"] = canon[_norm_mun(f["municipio"])]


# ── predios georreferenciados (mapa / KPIs / tabla) ────────────────────────
rows = con.execute("""
SELECT p.id, p.nombre, p.municipio, p.vereda, p.latitud lat, p.longitud lon,
       a.fecha, a.concepto, a.f_pct, a.my_pct, a.mn_pct,
       (SELECT COUNT(*) FROM respuestas r WHERE r.auditoria_id=a.id AND r.respuesta='NO') hallazgos
FROM predios p
JOIN auditorias a ON a.id=(SELECT id FROM auditorias WHERE predio_id=p.id
                           ORDER BY fecha DESC, id DESC LIMIT 1)
WHERE p.latitud IS NOT NULL AND p.latitud!=0 AND p.longitud IS NOT NULL AND p.longitud!=0
ORDER BY p.nombre""").fetchall()
datos = [dict(r) for r in rows]
munis = sorted(set(d["municipio"] for d in datos if d["municipio"]))

# ── hallazgos con estado de seguimiento, por auditoría ─────────────────────
hall = {}
for r in con.execute("""
    SELECT r.auditoria_id, c.id cid, c.nombre, c.tipo,
           COALESCE(s.estado,'pendiente') estado, COALESCE(s.obligatorio,0) oblig,
           s.evidencia, s.notas, s.fecha_limite
    FROM respuestas r
    JOIN criterios c ON c.id=r.criterio_id
    LEFT JOIN seguimiento s ON s.criterio_id=c.id AND s.auditoria_id=r.auditoria_id
    WHERE r.respuesta='NO'"""):
    hall.setdefault(r["auditoria_id"], []).append({
        "id": r["cid"], "nombre": r["nombre"], "tipo": r["tipo"], "estado": r["estado"],
        "oblig": int(r["oblig"]), "evidencia": r["evidencia"] or "", "notas": r["notas"] or "",
        "limite": r["fecha_limite"] or "",
    })
_orden = {"F": 1, "My": 2, "Mn": 3}
for v in hall.values():
    v.sort(key=lambda h: (_orden.get(h["tipo"], 9), [int(x) for x in h["id"].split(".")]))

def _hash_cedula(valor):
    """Huella SHA-256 de la cédula (sólo los dígitos).

    El número crudo NO se publica: el HTML lleva únicamente esta huella, que es lo
    que compara el buscador. Mismo algoritmo en JS (crypto.subtle, SHA-256).
    """
    digitos = re.sub(r"\D", "", str(valor or ""))
    return hashlib.sha256(digitos.encode()).hexdigest() if digitos else ""


# ── fichas de TODOS los predios (incluidos los sin coordenadas) ────────────
fichas = []
for r in con.execute("""
    SELECT p.id, p.nombre, p.identificacion, p.municipio, p.vereda,
           p.latitud, p.longitud, a.id aid, a.fecha, a.concepto,
           a.f_cumplidos, a.f_total, a.f_pct, a.my_cumplidos, a.my_total, a.my_pct,
           a.mn_cumplidos, a.mn_total, a.mn_pct, a.observaciones
    FROM predios p
    JOIN auditorias a ON a.id=(SELECT id FROM auditorias WHERE predio_id=p.id
                               ORDER BY fecha DESC, id DESC LIMIT 1)
    ORDER BY p.nombre"""):
    hs = hall.get(r["aid"], [])
    prog = {
        "total": len(hs),
        "cerrados": sum(1 for h in hs if h["estado"] == "cerrado"),
        "en_proceso": sum(1 for h in hs if h["estado"] == "en_proceso"),
        "oblig_total": sum(1 for h in hs if h["oblig"]),
        "oblig_cerrados": sum(1 for h in hs if h["oblig"] and h["estado"] == "cerrado"),
    }
    geo = bool(r["latitud"] and r["longitud"])
    fichas.append({
        "id": r["id"], "nombre": r["nombre"],
        "cid": _hash_cedula(r["identificacion"]),
        "municipio": r["municipio"] or "", "vereda": r["vereda"] or "",
        "lat": r["latitud"] if geo else None, "lon": r["longitud"] if geo else None,
        "fecha": r["fecha"], "concepto": r["concepto"],
        "f": {"cum": r["f_cumplidos"], "tot": r["f_total"], "pct": r["f_pct"]},
        "my": {"cum": r["my_cumplidos"], "tot": r["my_total"], "pct": r["my_pct"]},
        "mn": {"cum": r["mn_cumplidos"], "tot": r["mn_total"], "pct": r["mn_pct"]},
        "observaciones": r["observaciones"] or "",
        "hallazgos": hs, "prog": prog,
    })

n_fichas = len(fichas)
_unificar_municipios(datos, fichas)   # 'CAJIBÍO' y 'Cajibío' son el mismo municipio

html = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard Auditorías BPG ICA</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root{--v:#0B3D2E;--g:#2E7D32;--r:#C62828;--o:#E65100}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#f4f7f5;color:#1c2b26}
header{background:var(--v);color:#fff;padding:18px 30px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px}
header h1{font-size:20px} header p{opacity:.85;font-size:12.5px;margin-top:2px}
.filtro{background:#fff;color:#0B3D2E;border:none;border-radius:8px;padding:9px 14px;font-size:14px;font-weight:600;cursor:pointer;min-width:150px}
.buscar{display:flex;gap:6px}
.buscar input{background:#fff;color:#1c2b26;border:none;border-radius:8px;padding:9px 13px;font-size:14px;width:210px}
.buscar button{background:var(--o);color:#fff;border:none;border-radius:8px;padding:9px 16px;font-size:14px;font-weight:700;cursor:pointer}
.buscar button:hover{background:#bf360c}
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
tbody tr.clic{cursor:pointer} tbody tr.clic:hover{background:#eef6f1}
.badge{padding:2px 7px;border-radius:12px;color:#fff;font-size:11px;font-weight:600}
.cert{background:var(--g)} .apl{background:var(--r)}
.full{grid-column:1/-1}
.scroll{max-height:380px;overflow:auto;border-radius:8px}
#resumenFiltro{font-size:12px;color:#6b7c76;margin-bottom:8px}
/* ── ficha / consulta ── */
#panelFicha{display:none;margin-bottom:18px}
.ficha{background:#fff;border-radius:12px;box-shadow:0 3px 12px rgba(0,0,0,.1);overflow:hidden}
.ficha .fhead{background:var(--v);color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.ficha .fhead h2{font-size:18px}
.ficha .fhead .sub{font-size:12px;opacity:.85;margin-top:2px}
.ficha .cerrar{background:rgba(255,255,255,.16);border:none;color:#fff;border-radius:8px;padding:6px 12px;font-size:13px;font-weight:700;cursor:pointer}
.ficha .cuerpo{padding:16px 18px}
.fmeta{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:8px 18px;font-size:12.5px;margin-bottom:14px}
.fmeta b{color:var(--v)}
.fcifras{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.fcif{background:#f7faf8;border:1px solid #dfe7e3;border-radius:9px;padding:11px 13px}
.fcif .t{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#6b7c76}
.fcif .v{font-size:22px;font-weight:700;margin-top:2px}
.fcif .u{font-size:11.5px;color:#6b7c76}
.si{color:var(--g)} .no{color:var(--r)}
.avance{background:#f2f7f4;border:1px solid #dfe7e3;border-radius:9px;padding:12px 14px;font-size:12.5px;margin-bottom:16px}
.avance .bar{height:9px;background:#e0e7e3;border-radius:5px;overflow:hidden;margin-top:8px}
.avance .bar i{display:block;height:100%;background:var(--g)}
.fsec{font-size:13px;color:var(--v);font-weight:700;margin:4px 0 8px}
.hrow{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-bottom:1px solid #eef2f0;font-size:12.5px}
.hrow:last-child{border-bottom:none}
.hrow .hid{font-weight:700;color:var(--v);min-width:38px}
.htag{font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;color:#fff;white-space:nowrap}
.htag.F{background:var(--r)}.htag.My{background:var(--o)}.htag.Mn{background:#F9A825}
.est{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;padding:2px 8px;border-radius:10px;border:1px solid;white-space:nowrap}
.est.pendiente{color:#8a6d00;border-color:#e0c060;background:#fff8e1}
.est.en_proceso{color:#0d5c8c;border-color:#8fc2e0;background:#e8f4fb}
.est.cerrado{color:#1b5e20;border-color:#9ccc9f;background:#e8f5e9}
.hnota{font-size:11.5px;color:#6b7c76;margin-top:3px}
.oblig{font-size:10px;font-weight:700;color:var(--v);text-transform:uppercase}
#noEncontrado{display:none;background:#fff5e6;border-left:4px solid var(--o);border-radius:8px;padding:12px 16px;font-size:13px;margin-bottom:18px}
@media(max-width:820px){.grid{grid-template-columns:1fr}.fcifras{grid-template-columns:1fr}.buscar input{width:160px}}
</style></head><body>
<header>
 <div><h1>📊 Dashboard Auditorías BPG ICA</h1>
 <p>Resolución 067449 · Forma 3-852 V6 · <span id="ttlPredios">0</span> predios</p></div>
 <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
  <div><label style="font-size:12px;opacity:.8;margin-right:6px">Municipio:</label><select id="selMun" class="filtro"></select></div>
  <div class="buscar">
   <input id="inpBuscar" type="search" inputmode="numeric" placeholder="N° identificación del productor">
   <button id="btnBuscar" type="button">Consultar</button>
  </div>
 </div>
</header>
<div class="wrap">
 <div id="noEncontrado"></div>
 <div id="panelFicha"><div class="ficha" id="ficha"></div></div>
 <div class="cards">
  <div class="card"><div class="lab">Predios</div><div class="num" id="kPredios">0</div></div>
  <div class="card"><div class="lab" style="color:var(--g)">Certificables</div><div class="num" style="color:var(--g)" id="kCert">0</div></div>
  <div class="card"><div class="lab" style="color:var(--r)">Aplazados</div><div class="num" style="color:var(--r)" id="kApl">0</div></div>
 </div>
 <div class="plt" style="margin-bottom:18px"><h3>🗺️ Mapa de predios (ubicación y certificación)</h3><div id="mapa"></div></div>
 <div class="grid">
  <div class="plt"><h3>Estado de certificación</h3><canvas id="cConcepto" height="160"></canvas></div>
  <div class="plt"><h3>Predios por municipio <span style="font-size:11px;color:#6b7c76;font-weight:400">(clic en barra para filtrar)</span></h3><canvas id="cMunicipio" height="160"></canvas></div>
  <div class="plt full"><h3>Detalle de predios <span style="font-size:11px;color:#6b7c76;font-weight:400">(clic en una fila para ver la ficha y su seguimiento)</span></h3>
   <div id="resumenFiltro"></div>
   <div class="scroll"><table><thead><tr><th>Predio</th><th>Municipio</th><th>Concepto</th><th>F%</th><th>My%</th><th>Mn%</th><th>Hallazgos</th></tr></thead>
   <tbody id="tabla"></tbody></table></div>
  </div>
 </div>
</div>
<script>
const TODOS=__DATOS__;
const FICHAS=__FICHAS__;
let MUN='Todos';
const munis=[...new Set(TODOS.map(d=>d.municipio))].sort();
/* El mapa y los gráficos vienen de un CDN: si la conexión falla (o el CDN está caído),
   el resto del tablero —y sobre todo el buscador— debe seguir funcionando. */
let map=null;
if(typeof L!=='undefined'){
  try{
    map=L.map('mapa').setView([2.43,-76.55],9);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(map);
  }catch(err){map=null;}
}
const mk=color=>typeof L==='undefined'?null:L.divIcon({className:'',html:'<div style="width:14px;height:14px;border-radius:50%;background:'+color+';border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,.5)"></div>'});
const iconV=mk('#2E7D32'), iconR=mk('#C62828');
let capaPredios=null, chConc=null, chMun=null, marcados={};
const e=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/g,'');
function renderMapa(ds){
  if(!map){
    const c=document.getElementById('mapa');
    if(c)c.innerHTML='<div style="padding:26px;text-align:center;color:#666">⚠️ No se pudo cargar el mapa (sin conexión con el servicio de mapas).<br>El resto del tablero y la consulta por identificación siguen funcionando.</div>';
    return;
  }
  if(capaPredios)map.removeLayer(capaPredios);
  marcados={};
  const feats=ds.map(d=>({type:'Feature',properties:d,geometry:{type:'Point',coordinates:[d.lon,d.lat]}}));
  capaPredios=L.geoJSON({type:'FeatureCollection',features:feats},{
    pointToLayer:function(f,ll){
      const m=L.marker(ll,{icon:f.properties.concepto==='Certificable'?iconV:iconR});
      marcados[f.properties.id]=m; return m;
    },
    onEachFeature:function(f,l){l.bindPopup('<b>'+e(f.properties.nombre)+'</b> · '+e(f.properties.municipio)+'<br>'+e(f.properties.concepto)+' ('+e(f.properties.fecha)+')<br>F '+f.properties.f_pct+'% · My '+f.properties.my_pct+'% · Mn '+f.properties.mn_pct+'%')}}).addTo(map);
  if(feats.length){const b=L.geoJSON({type:'FeatureCollection',features:feats}).getBounds();if(b.isValid())map.fitBounds(b.pad(0.25));}
  else{map.setView([2.43,-76.55],9);}
}
function renderConc(ds){
  if(typeof Chart==='undefined')return;
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
      onClick:function(ev,el){if(el.length){MUN=labels[el[0].index];document.getElementById('selMun').value=MUN;actualizar();}}}});
}
function renderKpis(ds){
  const c=ds.filter(d=>d.concepto==='Certificable').length;
  document.getElementById('kPredios').textContent=ds.length;
  document.getElementById('kCert').textContent=c;
  document.getElementById('kApl').textContent=ds.length-c;
  document.getElementById('ttlPredios').textContent=ds.length;
  document.getElementById('resumenFiltro').textContent=MUN==='Todos'?('Mostrando los '+ds.length+' predios georreferenciados'):('Focalizado en '+MUN+' — '+ds.length+' predios');
}
function renderTabla(ds){
  document.getElementById('tabla').innerHTML=ds.map(d=>
    '<tr class="clic" data-pid="'+d.id+'"><td>'+e(d.nombre)+'</td><td>'+e(d.municipio)+'</td>'
    +'<td><span class="badge '+(d.concepto==='Certificable'?'cert':'apl')+'">'+e(d.concepto)+'</span></td>'
    +'<td>'+Math.round(d.f_pct)+'%</td><td>'+Math.round(d.my_pct)+'%</td><td>'+Math.round(d.mn_pct)+'%</td>'
    +'<td>'+d.hallazgos+'</td></tr>').join('');
  document.querySelectorAll('#tabla tr.clic').forEach(tr=>{
    tr.addEventListener('click',()=>{const f=FICHAS.find(x=>String(x.id)===tr.dataset.pid); if(f) mostrarFicha(f);});
  });
}
function actualizar(){
  const ds=MUN==='Todos'?TODOS:TODOS.filter(d=>d.municipio===MUN);
  /* cada panel por separado: si uno falla (CDN caído, etc.) los demás siguen */
  [()=>renderKpis(ds),()=>renderMapa(ds),()=>renderConc(ds),()=>renderMun(),()=>renderTabla(ds)]
    .forEach(fn=>{try{fn();}catch(err){console.warn('panel no disponible:',err);}});
}
/* ── consulta por identificación (la cédula no está en la página: sólo su huella) ── */
async function hashCedula(s){
  if(!(window.crypto&&crypto.subtle)) throw new Error('sin-crypto');
  const buf=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s));
  return Array.from(new Uint8Array(buf)).map(b=>b.toString(16).padStart(2,'0')).join('');
}
async function buscar(texto){
  const q=norm(texto);
  const digitos=(texto||'').replace(/\D/g,'');
  document.getElementById('noEncontrado').style.display='none';
  document.getElementById('panelFicha').style.display='none';
  if(!q){return;}
  let f=null;
  if(digitos.length>=6){
    let huella;
    try{huella=await hashCedula(digitos);}
    catch(err){
      const n=document.getElementById('noEncontrado');
      n.innerHTML='🔒 Para buscar por número de identificación abre esta página desde su dirección web (https), no como archivo local.';
      n.style.display='block';return;
    }
    f=FICHAS.find(x=>x.cid===huella);
  }
  if(!f){f=FICHAS.find(x=>norm(x.nombre).indexOf(q)>=0);}
  if(!f){
    const n=document.getElementById('noEncontrado');
    n.innerHTML='🔍 No se encontró ningún predio con <b>'+e(texto)+'</b>. Escribe el número de identificación del productor (sin puntos ni espacios) o el nombre del predio.';
    n.style.display='block';
    return;
  }
  mostrarFicha(f);
}
/* ── plan de acción en PDF (checklist para el productor) ─────────────────── */
function planHTML(f){
  const pg=f.prog||{total:0,cerrados:0,en_proceso:0,oblig_total:0,oblig_cerrados:0};
  const pct=pg.total?Math.round(100*pg.cerrados/pg.total):0;
  const crit=(lab,m,um)=>{
    const p=(m&&m.tot)?m.pct:null, ok=(p!=null&&p>=um);
    return '<tr><td>'+lab+'</td><td class="c">'+(p==null?'—':p+'%')+'</td>'
      +'<td class="c">'+((m&&m.tot)?(m.cum+'/'+m.tot):'—')+'</td><td class="c">'+um+'%</td>'
      +'<td class="c" style="font-weight:bold;color:'+(ok?'#2E7D32':'#C62828')+'">'
      +(ok?'CUMPLE':'NO CUMPLE')+'</td></tr>';};
  const items=(f.hallazgos||[]).map(h=>{
    const det=[h.limite?('Plazo: '+h.limite):'', h.evidencia?('Evidencia: '+h.evidencia):'',
               h.notas?('Nota: '+h.notas):''].filter(Boolean).join(' · ');
    return '<div class="item'+(h.oblig?' oblig':'')+'">'
      +'<div class="cab"><span class="chk">☐</span><b>'+e(h.id)+' · '+e(h.nombre)+'</b>'
      +'<span class="tag">'+e(h.tipo)+'</span>'+(h.oblig?'<span class="obl">OBLIGATORIO</span>':'')
      +'<span class="est">'+e(String(h.estado||'pendiente').replace('_',' '))+'</span></div>'
      +(det?'<div class="det">'+e(det)+'</div>':'')
      +'<div class="firma">Cumplido / observaciones: ______________________________________________</div></div>';}).join('');
  return '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
   +'<title>Plan de accion BPG - '+e(f.nombre)+'</title><style>'
   +'@page{size:A4;margin:13mm}'
   +'*{box-sizing:border-box}body{font-family:"Segoe UI",Arial,sans-serif;font-size:11.5px;color:#1c2b26;margin:0}'
   +'h1{font-size:15px;color:#0B3D2E;margin:0}h2{font-size:13px;color:#0B3D2E;margin:12px 0 6px}'
   +'.sub{font-size:10.5px;color:#555;margin:2px 0 10px;border-bottom:2px solid #0B3D2E;padding-bottom:6px}'
   +'table{width:100%;border-collapse:collapse;margin:6px 0 10px}'
   +'th,td{border:1px solid #b9c4bf;padding:4px 6px;font-size:11px;text-align:left}'
   +'th{background:#eef3f0}td.c{text-align:center}'
   +'.item{border:1px solid #ccd5d1;border-left:5px solid #9e9e9e;border-radius:3px;padding:6px 8px;margin-bottom:6px;page-break-inside:avoid}'
   +'.item.oblig{border-left-color:#E65100}'
   +'.cab{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}'
   +'.chk{font-size:15px;line-height:1}'
   +'.tag{background:#eceff1;border-radius:3px;padding:0 4px;font-size:10px}'
   +'.obl{background:#FFF3E0;color:#E65100;border:1px solid #E65100;border-radius:3px;padding:0 4px;font-size:10px}'
   +'.est{margin-left:auto;font-size:10px;text-transform:uppercase;color:#555}'
   +'.det{color:#444;font-size:10.5px;margin-top:3px}'
   +'.firma{color:#8a8a8a;font-size:10.5px;margin-top:5px}'
   +'.firmas{margin-top:16px;display:flex;gap:30px}'
   +'.firmas div{flex:1;border-top:1px solid #333;padding-top:3px;font-size:10.5px}'
   +'.nota{font-size:10px;color:#666;margin-top:10px;border-top:1px solid #ccc;padding-top:6px}'
   +'</style></head><body>'
   +'<h1>PLAN DE ACCIÓN — BUENAS PRÁCTICAS GANADERAS</h1>'
   +'<div class="sub">Resolución ICA 067449 · Forma 3-852 V6 · Lista de verificación para el productor</div>'
   +'<table><tr><th>Predio</th><td>'+e(f.nombre)+'</td><th>Municipio</th><td>'+e(f.municipio||'—')+'</td></tr>'
   +'<tr><th>Vereda</th><td>'+e(f.vereda||'—')+'</td><th>Auditoría</th><td>'+e(f.fecha||'—')+'</td></tr>'
   +'<tr><th>Concepto</th><td colspan="3"><b>'+e(f.concepto)+'</b></td></tr></table>'
   +'<table><tr><th>Categoría</th><th class="c">Resultado</th><th class="c">Criterios</th>'
   +'<th class="c">Umbral</th><th class="c">Estado</th></tr>'
   +crit('Fundamentales (F)',f.f,100)+crit('Mayores (My)',f.my,80)+crit('Menores (Mn)',f.mn,60)+'</table>'
   +'<div style="font-size:11px;margin-bottom:8px"><b>Avance del plan:</b> '+pg.cerrados+' de '+pg.total
   +' hallazgo(s) cerrados ('+pct+'%) · en proceso: '+pg.en_proceso
   +' · obligatorios para certificar: '+pg.oblig_cerrados+'/'+pg.oblig_total+'</div>'
   +'<h2>Hallazgos y acciones de mejora ('+(f.hallazgos||[]).length+')</h2>'
   +((f.hallazgos||[]).length?items:'<div class="det">Sin hallazgos: todos los criterios aplicables cumplen.</div>')
   +'<div class="firmas"><div>Productor / representante</div><div>Asesor BPG</div><div>Fecha</div></div>'
   +'<div class="nota">Documento de preparación para la certificación en BPG: <b>no constituye certificación oficial del ICA</b>. '
   +'Los datos personales del productor no se incluyen (documento generado desde el tablero público).</div>'
   +'<scr'+'ipt>window.onload=function(){setTimeout(function(){window.print()},350)}</scr'+'ipt>'
   +'</body></html>';
}
function descargarPlan(f){
  const w=window.open('','_blank');
  if(!w){alert('Permite las ventanas emergentes de este sitio para descargar el plan de acción.');return;}
  w.document.open();w.document.write(planHTML(f));w.document.close();
}
function mostrarFicha(f){
  document.getElementById('noEncontrado').style.display='none';
  const ok=f.concepto.toLowerCase().indexOf('certificable')>=0;
  const cif=(t,lab,um)=>{const m=f[t];const pct=m.pct==null?0:m.pct;const cumple=pct>=um;
    return '<div class="fcif"><div class="t">'+lab+'</div>'
     +'<div class="v '+(cumple?'si':'no')+'">'+(m.tot?pct+'%':'—')+'</div>'
     +'<div class="u">'+(m.tot?(m.cum+'/'+m.tot+' · umbral '+um+'% '+(cumple?'✓':'✗')):'sin datos')+'</div></div>';};
  const pg=f.prog||{total:0,cerrados:0,en_proceso:0,oblig_total:0,oblig_cerrados:0};
  const pctProg=pg.total?Math.round(100*pg.cerrados/pg.total):0;
  const hs=(f.hallazgos||[]);
  const bordes=hs.map(h=>{
    const nota=[h.limite?('Plazo: '+h.limite):'', h.evidencia?('Evidencia: '+h.evidencia):'', h.notas?('Nota: '+h.notas):''].filter(Boolean).join(' · ');
    return '<div class="hrow"><span class="hid">'+e(h.id)+'</span>'
      +'<span class="htag '+e(h.tipo)+'">'+e(h.tipo)+'</span>'
      +'<span style="flex:1">'+e(h.nombre)
        +'<div class="hnota">'+(nota?e(nota):'Sin registro de avance')+'</div></span>'
      +(h.oblig?'<span class="oblig">Obligatorio</span> ':'')
      +'<span class="est '+e(h.estado)+'">'+e(h.estado.replace('_',' '))+'</span></div>';}).join('');
  document.getElementById('ficha').innerHTML=
   '<div class="fhead"><div><h2>'+e(f.nombre)+'</h2>'
   +'<div class="sub">'+e(f.concepto)+' · auditoría del '+e(f.fecha)+' · Res. ICA 067449 (Forma 3-852 V6)</div></div>'
   +'<button class="cerrar" id="btnPlan" title="Descargar el plan de acción como checklist en PDF" style="background:#2E7D32;color:#fff;border-color:#2E7D32;font-weight:600">📄 Plan de acción (PDF)</button>'
   +'<button class="cerrar" id="btnCerrar">✕ Cerrar</button></div>'
   +'<div class="cuerpo">'
   +'<div class="fmeta">'
    +'<div><b>Municipio:</b> '+e(f.municipio||'—')+'</div>'
    +'<div><b>Vereda:</b> '+e(f.vereda||'—')+'</div>'
    +'<div><b>Registro en mapa:</b> '+(f.lat?'sí':'sin coordenadas')+'</div>'
   +'</div>'
   +'<div class="hnota" style="margin:8px 0 2px">🔒 Los datos personales del productor (nombre, identificación y teléfono) no se publican en esta consulta.</div>'
   +'<div class="fcifras">'+cif('f','Fundamentales (F)',100)+cif('my','Mayores (My)',80)+cif('mn','Menores (Mn)',60)+'</div>'
   +'<div class="avance"><b>Avance del plan de acción:</b> '+pg.cerrados+' de '+pg.total+' hallazgo(s) cerrados ('+pctProg+'%)'
     +' · '+pg.en_proceso+' en proceso · <b>obligatorios para certificar: '+pg.oblig_cerrados+'/'+pg.oblig_total+'</b>'
     +'<div class="bar"><i style="width:'+pctProg+'%"></i></div></div>'
   +'<div class="fsec">Hallazgos y seguimiento de mejoras ('+hs.length+')</div>'
   +(hs.length?bordes:'<div class="hnota">Sin hallazgos: todos los criterios aplicables cumplen.</div>')
   +'</div>';
  document.getElementById('panelFicha').style.display='block';
  document.getElementById('btnCerrar').addEventListener('click',()=>{
    document.getElementById('panelFicha').style.display='none';
    document.getElementById('inpBuscar').value='';
  });
  document.getElementById('btnPlan').addEventListener('click',()=>descargarPlan(f));
  document.getElementById('panelFicha').scrollIntoView({behavior:'smooth',block:'start'});
  if(map&&f.lat&&f.lon&&marcados[f.id]){map.setView([f.lat,f.lon],14);marcados[f.id].openPopup();}
}
const sel=document.getElementById('selMun');
['Todos'].concat(munis).forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent=m;sel.appendChild(o)});
sel.value=MUN;
sel.addEventListener('change',function(){MUN=sel.value;actualizar()});
const inp=document.getElementById('inpBuscar');
document.getElementById('btnBuscar').addEventListener('click',()=>buscar(inp.value));
inp.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();buscar(inp.value);}});
actualizar();
</script></body></html>"""

html = html.replace("__DATOS__", json.dumps(datos, ensure_ascii=False))
html = html.replace("__FICHAS__", json.dumps(fichas, ensure_ascii=False))
open(OUT, "w", encoding="utf-8").write(html)
n_hall = sum(len(f["hallazgos"]) for f in fichas)
print(f"OK {OUT} ({len(datos)} predios en mapa, {n_fichas} fichas consultables, "
      f"{n_hall} hallazgos con seguimiento)")
