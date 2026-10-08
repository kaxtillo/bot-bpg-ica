// Extrae la plantilla REAL del dashboard (del HTML publicado) y genera el documento
// del plan de acción para un predio, sin duplicar código.
const fs = require('fs'), vm = require('vm');
const RUTA = '/home/hermes/auditorias_bpg/Dashboard_Auditorias_BPG_ICA.html';
const PREDIO = process.argv[2] || 'EL ENCANTO';
const SALIDA = process.argv[3] || '/tmp/plan_check.html';

const html = fs.readFileSync(RUTA, 'utf8');
const FICHAS = JSON.parse(html.match(/const FICHAS=(.*);\n/)[1]);

// el bloque de funciones: desde la creación del mapa (que se salta sola sin Leaflet)
// hasta mostrarFicha (así se incluyen e(), planHTML() y descargarPlan())
const ini = html.indexOf('let map=null;');
const fin = html.indexOf('function mostrarFicha(f){');
if (ini < 0 || fin < 0) { console.error('no pude localizar el bloque JS'); process.exit(1); }
const bloque = html.slice(ini, fin);

const ctx = { console, FICHAS };
vm.createContext(ctx);
vm.runInContext(bloque, ctx);

const f = FICHAS.find(x => x.nombre === PREDIO);
if (!f) { console.error('predio no encontrado:', PREDIO); process.exit(1); }

const doc = ctx.planHTML(f);
fs.writeFileSync(SALIDA, doc);
const casillas = (doc.match(/☐/g) || []).length;
const personal = /YIMI|76327096|3052963963/i.test(doc);
console.log(`predio: ${f.nombre}`);
console.log(`hallazgos (casillas ☐): ${casillas}`);
console.log(`documento: ${doc.length} chars -> ${SALIDA}`);
console.log(`documento completo: ${doc.startsWith('<!DOCTYPE html>') && doc.trim().endsWith('</html>')}`);
console.log(`llamada a imprimir: ${/window\.print/.test(doc)}`);
console.log(`contiene datos personales: ${personal}`);
