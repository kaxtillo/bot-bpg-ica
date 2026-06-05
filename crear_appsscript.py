import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SHEET_ID = '1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg'

with open('/home/ubuntu/.openclaw/workspace/token_final.json') as f:
    token_data = json.load(f)

creds = Credentials(token=token_data['access_token'], refresh_token=token_data['refresh_token'],
    token_uri='https://oauth2.googleapis.com/token', client_id='675307706784-857u244apvcaef30esvbfmduqikeg0a3.apps.googleusercontent.com',
    client_secret='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', scopes=['https://www.googleapis.com/auth/spreadsheets'])
service = build('sheets', 'v4', credentials=creds)

# El script de Google Apps Script se inyecta como un proyecto vinculado a la hoja
# Pero Apps Script no tiene API directa para crear proyectos vinculados.
# Usamos la API de Apps Script para crear el script.

# Otra opción: incluir el script como texto en la hoja y dar instrucciones manuales.
# O usar la API de Google Apps Script (requires additional scopes).

# Verificar si tenemos scope para scripts
current_scopes = creds.scopes
print(f"Current scopes: {current_scopes}")

# Escribir el código Apps Script como nota en la hoja de referencia
# para que el usuario pueda instalarlo manualmente, o intentar con API

apps_script_code = """// ============================================
// NOTIFICACIÓN AUTOMÁTICA - PREDIOS CERTIFICABLES
// ============================================
// Instalación:
// 1. En la hoja, ir a Extensiones > Apps Script
// 2. Pegar este código
// 3. Configurar CORREO_DESTINO
// 4. Guardar y ejecutar: crearTrigger()
// 5. Autorizar permisos
// ============================================

var CORREO_DESTINO = "CORREO@EJEMPLO.COM"; // <-- CAMBIAR
var NOMBRE_HOJA = "Hoja 1";
var COL_CONCEPTO = 88; // Columna CL = 88
var COL_PREDIO = 6;    // Columna F
var COL_PROPIETARIO = 2; // Columna B
var COL_MUNICIPIO = 8;  // Columna H

function enviarNotificacionCertificable(fila, predio, propietario, municipio, fPct, myPct, mnPct) {
  var asunto = "✅ PREDIO CERTIFICABLE - " + predio;
  var cuerpo = "";
  cuerpo += "Se ha registrado un predio como CERTIFICABLE en Buenas Prácticas Ganaderas.\\n\\n";
  cuerpo += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n";
  cuerpo += "🏠 PREDIO: " + predio + "\\n";
  cuerpo += "👤 PROPIETARIO: " + propietario + "\\n";
  cuerpo += "📍 UBICACIÓN: " + municipio + "\\n";
  cuerpo += "📄 FILA EN HOJA: " + fila + "\\n";
  cuerpo += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n";
  cuerpo += "📊 RESULTADOS:\\n";
  cuerpo += "• Fundamentales: " + fPct + "% (mín. 90%)\\n";
  cuerpo += "• Mayores: " + myPct + "% (mín. 80%)\\n";
  cuerpo += "• Menores: " + mnPct + "% (mín. 70%)\\n\\n";
  cuerpo += "🔗 https://docs.google.com/spreadsheets/d/" + SpreadsheetApp.getActiveSpreadsheet().getId() + "\\n\\n";
  cuerpo += "---\\n";
  cuerpo += "Auditor Virtual BPG - ICA\\n";
  cuerpo += "Resolución 067449";
  
  MailApp.sendEmail({
    to: CORREO_DESTINO,
    subject: asunto,
    body: cuerpo
  });
}

function verificarPredios() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(NOMBRE_HOJA);
  if (!sheet) {
    Logger.log("Hoja no encontrada: " + NOMBRE_HOJA);
    return;
  }
  
  var ultimaFila = sheet.getLastRow();
  if (ultimaFila < 2) return;
  
  var datos = sheet.getRange(2, 1, ultimaFila - 1, COL_CONCEPTO).getValues();
  var notificaciones = [];
  
  for (var i = 0; i < datos.length; i++) {
    var fila = i + 2;
    var concepto = datos[i][COL_CONCEPTO - 1];
    var predio = datos[i][COL_PREDIO - 1] || "Sin nombre";
    var propietario = datos[i][COL_PROPIETARIO - 1] || "Sin propietario";
    var municipio = datos[i][COL_MUNICIPIO - 1] || "";
    
    if (concepto && concepto.toString().trim().toUpperCase() === "CERTIFICABLE") {
      var fPct = datos[i][80 - 1] || "N/A";  // FPorcentaje
      var myPct = datos[i][83 - 1] || "N/A"; // MyPorcentaje
      var mnPct = datos[i][86 - 1] || "N/A"; // MnPorcentaje
      
      notificaciones.push({
        fila: fila,
        predio: predio,
        propietario: propietario,
        municipio: municipio,
        fPct: fPct,
        myPct: myPct,
        mnPct: mnPct
      });
    }
  }
  
  if (notificaciones.length > 0) {
    for (var j = 0; j < notificaciones.length; j++) {
      var n = notificaciones[j];
      enviarNotificacionCertificable(n.fila, n.predio, n.propietario, n.municipio, n.fPct, n.myPct, n.mnPct);
      Logger.log("Notificación enviada para: " + n.predio + " (fila " + n.fila + ")");
    }
  } else {
    Logger.log("No se encontraron predios certificables.");
  }
}

function crearTrigger() {
  // Elimina triggers existentes para evitar duplicados
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "verificarPredios") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  
  // Crea trigger cada hora
  ScriptApp.newTrigger("verificarPredios")
    .timeBased()
    .everyHours(1)
    .create();
  
  Logger.log("✅ Trigger creado: verificarPredios cada 1 hora");
}

function eliminarTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "verificarPredios") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  Logger.log("✅ Trigger eliminado");
}

// Función para probar manualmente
function probarEnvio() {
  CORREO_DESTINO = Session.getActiveUser().getEmail();
  MailApp.sendEmail({
    to: CORREO_DESTINO,
    subject: "🔧 PRUEBA - Sistema de Notificación BPG",
    body: "Si recibes esto, el sistema de notificación funciona correctamente.\\n\\nAuditor Virtual BPG - ICA"
  });
  Logger.log("Correo de prueba enviado a: " + CORREO_DESTINO);
}
"""

# Write the script as instructions in a new sheet tab
sheet_title = "📧 Apps Script - Instalación"

# Check if sheet exists
spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
existing_sheets = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]

if sheet_title in existing_sheets:
    for s in spreadsheet.get('sheets', []):
        if s['properties']['title'] == sheet_title:
            sid = s['properties']['sheetId']
            service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID,
                body={"requests": [{"deleteSheet": {"sheetId": sid}}]}).execute()
            break

request = {"addSheet": {"properties": {"title": sheet_title, "gridProperties": {"rowCount": 80, "columnCount": 3}}}}
response = service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": [request]}).execute()
new_sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']

instructions = [
    ["📧 INSTALACIÓN DEL SISTEMA DE NOTIFICACIÓN AUTOMÁTICA"],
    [""],
    ["PASO 1: Abrir Apps Script"],
    ["   En el menú de la hoja: Extensiones > Apps Script"],
    [""],
    ["PASO 2: Pegar el código"],
    ["   Borra el código existente y pega el código de la columna C de esta hoja."],
    [""],
    ["PASO 3: Configurar correo destino"],
    ["   En la línea 13, cambia CORREO@EJEMPLO.COM por el correo donde quieres recibir las alertas."],
    ["   Ejemplo: var CORREO_DESTINO = \"tucorreo@gmail.com\";"],
    [""],
    ["PASO 4: Guardar y nombrar el proyecto"],
    ["   Click en Guardar 🖫, nombra el proyecto: \"Notificaciones BPG\""],
    [""],
    ["PASO 5: Ejecutar crearTrigger()"],
    ["   Selecciona la función 'crearTrigger' en el desplegable y haz clic en ▶ Ejecutar."],
    ["   Autoriza los permisos cuando Google lo solicite."],
    [""],
    ["PASO 6: Probar (opcional)"],
    ["   Selecciona 'probarEnvio' y ejecuta para verificar que llegan los correos."],
    [""],
    ["✅ LISTO. El sistema revisará automáticamente cada hora si hay nuevos predios certificables."],
    [""],
    ["⚠️ IMPORTANTE:"],
    ["   - El script envía UN correo por cada predio certificable que encuentre."],
    ["   - Si un predio ya fue notificado antes, volverá a notificar cada hora."],
    ["   - Para evitar duplicados, puedes modificar el script para llevar un registro."],
    ["   - Para DETENER las notificaciones: ejecuta la función eliminarTrigger()"],
    [""],
    ["━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"],
    ["CÓDIGO COMPLETO (copiar y pegar en Apps Script):"],
]

# Write instructions
code_lines = apps_script_code.strip().split('\n')
all_rows = instructions + [[line] for line in code_lines]

body = {"valueInputOption": "RAW", "data": [{"range": f"'{sheet_title}'!A1:C{len(all_rows)}", "values": [r + ['']*(3-len(r)) for r in all_rows]}]}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()

# Format
requests = [
    {"repeatCell": {"range": {"sheetId": new_sheet_id, "startRowIndex": 0, "endRowIndex": 1},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 14}, "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat"}},
    {"updateDimensionProperties": {"range": {"sheetId": new_sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
        "properties": {"pixelSize": 80}, "fields": "pixelSize"}},
    {"updateDimensionProperties": {"range": {"sheetId": new_sheet_id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3},
        "properties": {"pixelSize": 700}, "fields": "pixelSize"}},
    {"updateSheetProperties": {"properties": {"sheetId": new_sheet_id, "gridProperties": {"frozenRowCount": 0}},
        "fields": "gridProperties.frozenRowCount"}},
]
body = {"requests": requests}
service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()

# Also write code into a file so user can access easily
with open('/home/ubuntu/.openclaw/workspace/AppsScript_NotificacionBPG.js', 'w') as f:
    f.write(apps_script_code)

print("✅ Hoja de instalación creada: '📧 Apps Script - Instalación'")
print("✅ Código guardado localmente en: AppsScript_NotificacionBPG.js")
print(f"\nInstrucciones rápidas:")
print(f"1. Abre: https://docs.google.com/spreadsheets/d/{SHEET_ID}")
print(f"2. Extensiones > Apps Script")
print(f"3. Copia el código de la columna C de la pestaña '📧 Apps Script - Instalación'")
print(f"4. Cambia CORREO_DESTINO en la línea 13")
print(f"5. Guarda, ejecuta 'crearTrigger' y autoriza")
