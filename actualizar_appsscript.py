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

# Código limpio SIN caracteres Unicode/emojis problemáticos
codigo_limpio = """// NOTIFICACION AUTOMATICA - PREDIOS CERTIFICABLES BPG
// 1. Configurar CORREO_DESTINO abajo
// 2. Guardar y ejecutar: crearTrigger()
// 3. Autorizar permisos

var CORREO_DESTINO = "CORREO@EJEMPLO.COM"; // <-- CAMBIAR AQUI
var NOMBRE_HOJA = "Hoja 1";
var COL_CONCEPTO = 88;
var COL_PREDIO = 6;
var COL_PROPIETARIO = 2;
var COL_MUNICIPIO = 8;

function enviarNotificacionCertificable(fila, predio, propietario, municipio, fPct, myPct, mnPct) {
  var asunto = "[CERTIFICABLE] " + predio;
  var cuerpo = "";
  cuerpo += "Se ha registrado un predio como CERTIFICABLE en Buenas Practicas Ganaderas.\n\n";
  cuerpo += "--- DATOS DEL PREDIO ---\n";
  cuerpo += "Predio: " + predio + "\n";
  cuerpo += "Propietario: " + propietario + "\n";
  cuerpo += "Ubicacion: " + municipio + "\n";
  cuerpo += "Fila en hoja: " + fila + "\n\n";
  cuerpo += "--- RESULTADOS ---\n";
  cuerpo += "Fundamentales: " + fPct + "% (min. 90%)\n";
  cuerpo += "Mayores: " + myPct + "% (min. 80%)\n";
  cuerpo += "Menores: " + mnPct + "% (min. 70%)\n\n";
  cuerpo += "Link: https://docs.google.com/spreadsheets/d/" + SpreadsheetApp.getActiveSpreadsheet().getId() + "\n\n";
  cuerpo += "---\nAuditor Virtual BPG - ICA\nResolucion 067449";
  
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
      var fPct = datos[i][79] || "N/A";
      var myPct = datos[i][82] || "N/A";
      var mnPct = datos[i][85] || "N/A";
      
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
      Logger.log("Notificacion enviada para: " + n.predio + " (fila " + n.fila + ")");
    }
  } else {
    Logger.log("No se encontraron predios certificables.");
  }
}

function crearTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "verificarPredios") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  
  ScriptApp.newTrigger("verificarPredios")
    .timeBased()
    .everyHours(1)
    .create();
  
  Logger.log("Trigger creado: verificarPredios cada 1 hora");
}

function eliminarTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "verificarPredios") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  Logger.log("Trigger eliminado");
}

function probarEnvio() {
  MailApp.sendEmail({
    to: Session.getActiveUser().getEmail(),
    subject: "[PRUEBA] Sistema Notificacion BPG",
    body: "Si recibes esto, el sistema funciona correctamente.\n\nAuditor Virtual BPG - ICA"
  });
  Logger.log("Correo de prueba enviado");
}
"""

# Escribir solo el código en la columna C, empezando después de las instrucciones
# Primero limpio las instrucciones y pongo el código limpio
sheet_title = "Apps Script - Instalacion"

# Limpiar y reescribir
code_lines = codigo_limpio.strip().split('\n')
all_data = []
all_data.append(["INSTRUCCIONES"])
all_data.append([""])
all_data.append(["1. Abre Extensiones > Apps Script"])
all_data.append(["2. Borra el codigo existente y copia el que esta en la columna C (desde linea 11 en adelante)"])
all_data.append(["3. Cambia CORREO_DESTINO en la linea 11 por tu correo"])
all_data.append(["4. Guarda el proyecto (Ctrl+S)"])
all_data.append(["5. Selecciona 'crearTrigger' en el desplegable y presiona Ejecutar"])
all_data.append(["6. Autoriza los permisos cuando Google lo solicite"])
all_data.append([""])
all_data.append(["Para probar: selecciona 'probarEnvio' y ejecuta"])
all_data.append(["Para detener: selecciona 'eliminarTrigger' y ejecuta"])
all_data.append([""])
all_data.append(["========== CODIGO A COPIAR =========="])
for line in code_lines:
    all_data.append([line])

body = {"valueInputOption": "RAW", "data": [{"range": f"A1:A{len(all_data)}", "values": all_data}]}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()

# Write clean code to local file too
with open('/home/ubuntu/.openclaw/workspace/AppsScript_NotificacionBPG.js', 'w') as f:
    f.write(codigo_limpio)

print("Hoja actualizada con codigo limpio (sin caracteres especiales)")
print("Archivo local actualizado")
print()
print("INSTRUCCIONES:")
print("1. Ve a Extensiones > Apps Script")
print("2. Borra todo y pega el codigo de abajo (sin los emojis/simbolos raros):")
print()
print(codigo_limpio)
