// NOTIFICACION AUTOMATICA - PREDIOS CERTIFICABLES BPG
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
  cuerpo += "Se ha registrado un predio como CERTIFICABLE en Buenas Practicas Ganaderas.

";
  cuerpo += "--- DATOS DEL PREDIO ---
";
  cuerpo += "Predio: " + predio + "
";
  cuerpo += "Propietario: " + propietario + "
";
  cuerpo += "Ubicacion: " + municipio + "
";
  cuerpo += "Fila en hoja: " + fila + "

";
  cuerpo += "--- RESULTADOS ---
";
  cuerpo += "Fundamentales: " + fPct + "% (min. 90%)
";
  cuerpo += "Mayores: " + myPct + "% (min. 80%)
";
  cuerpo += "Menores: " + mnPct + "% (min. 70%)

";
  cuerpo += "Link: https://docs.google.com/spreadsheets/d/" + SpreadsheetApp.getActiveSpreadsheet().getId() + "

";
  cuerpo += "---
Auditor Virtual BPG - ICA
Resolucion 067449";
  
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
    body: "Si recibes esto, el sistema funciona correctamente.

Auditor Virtual BPG - ICA"
  });
  Logger.log("Correo de prueba enviado");
}
