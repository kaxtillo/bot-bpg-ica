import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SHEET_ID = '1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg'

with open('/home/ubuntu/.openclaw/workspace/token_final.json') as f:
    token_data = json.load(f)

creds = Credentials(
    token=token_data['access_token'],
    refresh_token=token_data['refresh_token'],
    token_uri='https://oauth2.googleapis.com/token',
    client_id='675307706784-857u244apvcaef30esvbfmduqikeg0a3.apps.googleusercontent.com',
    client_secret='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',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

service = build('sheets', 'v4', credentials=creds)

criterios = [
    ("1.1","Plan Sanitario","F","5.1.1","¿El predio cuenta con un plan sanitario elaborado y suscrito por un MV o MVZ con matrícula profesional vigente?"),
    ("1.2","Certificación de Hatos Libres","My","5.1.2","¿El predio cuenta con certificación oficial vigente del hato como libre de brucelosis y tuberculosis?"),
    ("1.3","Protocolo de Aislamiento","F","5.1.3","¿El predio cuenta con un protocolo escrito de manejo y aislamiento de animales enfermos?"),
    ("1.4","Registro de Diagnósticos","F","5.1.4","¿Se lleva un registro escrito de los diagnósticos de enfermedades y mortalidades presentadas?"),
    ("1.5","Instructivo de Enfermedades","F","5.1.5","¿Existe un instructivo visible para reconocimiento y notificación de enfermedades de control oficial?"),
    ("1.6","Área de Enfermería","F","5.1.6","¿El predio dispone de un área o potrero señalizado como sitio de enfermería o tratamiento?"),
    ("1.7","Programa de Mastitis","F","5.1.7","¿El predio cuenta con un programa de prevención y control de mastitis documentado?"),
    ("2.1","Identificación de Animales","F","5.2.1","¿Los animales están identificados de manera única e individual?"),
    ("2.2","Registro Individual","My","5.2.2","¿Se lleva un registro o ficha individual para cada animal?"),
    ("3.1","Delimitación del Predio","My","5.3.1","¿El predio cuenta con cercos, broches, puertas en buen estado que permitan delimitar el predio?"),
    ("3.2","Registro de Visitas","My","5.3.2","¿Se lleva un registro escrito de ingreso de personas y vehículos?"),
    ("3.3","Cuarentena","My","5.3.3","¿El predio cuenta con procedimiento de ingreso y aislamiento con cuarentena no menor a 21 días?"),
    ("3.4","Material Genético","Mn","5.3.4","¿El material genético proviene de centros autorizados por el ICA?"),
    ("3.5","Identificación de Áreas","Mn","5.3.5","¿Cada área de producción está debidamente identificada en lugar visible?"),
    ("4.1","Zona de Espera","My","6.1","¿La zona de espera antes del ordeño está en condiciones higiénicas adecuadas?"),
    ("4.2","Instalaciones Ordeño Fijo","F","6.2","¿Las instalaciones de ordeño fijo tienen pisos, paredes y techos en buen estado?"),
    ("4.3","Instalaciones Ordeño Móvil","F","6.3","¿Las instalaciones de ordeño móvil en potrero están protegidas de la intemperie?"),
    ("4.4","Instalaciones Sanitarias","Mn","6.4","¿El predio cuenta con servicios sanitarios adecuados para el personal?"),
    ("4.5","Rutina de Ordeño","F","6.5.1","¿Existe un procedimiento documentado de la rutina de ordeño?"),
    ("4.6","Equipos y Utensilios","F","6.5.2","¿Los equipos y utensilios de ordeño son apropiados, están limpios y almacenados correctamente?"),
    ("4.7","Disposición Leche Anormal","F","6.5.4","¿La leche anormal y de retiro se descarta adecuadamente?"),
    ("4.8","Agua para Ordeño","My","6.5.5","¿El agua utilizada para la rutina de ordeño es potable?"),
    ("4.9","Conservación de la Leche","My","6.5.7","¿El sistema de almacenamiento mantiene la leche a temperatura adecuada?"),
    ("5.1","Cuarto del Tanque de Leche","F","7.1","¿El tanque de enfriamiento está en un cuarto cerrado y dedicado únicamente para tal fin?"),
    ("5.2","Registro de Temperatura","My","7.5","¿Se cuenta con un registro de temperatura que verifique el funcionamiento del tanque?"),
    ("6.1","Productos con Registro ICA","F","8.1","¿Se utilizan únicamente productos veterinarios con registro ICA?"),
    ("6.2","Productos No Vencidos","F","8.2","¿Los productos veterinarios están vigentes?"),
    ("6.3","Almacenamiento de Medicamentos","My","8.3","¿Los medicamentos están almacenados según condiciones del rotulado?"),
    ("6.4","Sustancias Prohibidas","F","8.6","¿No se utilizan sustancias prohibidas por el ICA?"),
    ("6.5","Materias Primas Medicamento","F","8.7","¿No se suministran materias primas químicas directamente a los animales?"),
    ("6.6","Tiempos de Retiro","F","8.8","¿Se respetan los tiempos de retiro consignados en los medicamentos?"),
    ("6.7","Prescripción Veterinaria","F","8.9","¿Los tratamientos tienen prescripción escrita de MV o MVZ?"),
    ("6.8","Registros de Tratamientos","F","8.10","¿Se lleva registro de los tratamientos realizados?"),
    ("6.9","Equipos de Administración","My","8.11","¿Equipos para aplicación están limpios y se usan agujas desechables?"),
    ("6.10","Inventario de Productos","My","8.13","¿Se lleva un control de inventario de productos veterinarios?"),
    ("6.11","Autorización para Aplicación","My","8.14","¿El responsable de aplicar medicamentos cuenta con capacitación y autorización?"),
    ("6.12","Notificación Eventos Adversos","My","8.16","¿Se notifican al ICA los eventos adversos?"),
    ("7.1","Alimentos con Registro ICA","F","9.1","¿Alimentos comerciales cuentan con registro ICA y están bien almacenados?"),
    ("7.2","Alimento Medicado","F","9.2","¿Utiliza alimentos para administrar medicamentos con registro ICA y fórmula médica?"),
    ("7.3","Prohibiciones Alimentarias","F","9.6","¿No se utilizan harinas de carne, sangre y hueso?"),
    ("7.4","Subproductos","My","9.4","¿Los subproductos están en buen estado y se registra su origen?"),
    ("7.5","Insumos Agrícolas","F","9.8","¿Se emplean plaguicidas con registro ICA respetando períodos de carencia?"),
    ("7.6","Inventario de Alimentos","Mn","9.10","¿Se lleva inventario de alimentos y materias primas?"),
    ("7.7","Calidad del Agua","My","9.11","¿Se realiza monitoreo anual de la calidad del agua para consumo animal?"),
    ("8.1","Limpieza de Áreas","My","10.1","¿Las áreas, equipos y utensilios están limpios y ordenados?"),
    ("8.2","Ubicación del Predio","My","10.2","¿El predio está ubicado en zonas alejadas de focos de contaminación?"),
    ("8.3","Protección Fuentes Hídricas","My","10.3","¿Se implementan acciones para proteger las fuentes de agua?"),
    ("8.4","Disposición de Estiércol","My","10.5","¿Se utilizan métodos apropiados para la disposición de estiércol?"),
    ("8.5","Manejo de Residuos","My","10.6","¿Los residuos sólidos se clasifican y disponen adecuadamente?"),
    ("8.6","Almacenamiento de Insumos","My","10.9","¿Alimentos, medicamentos y plaguicidas se almacenan en áreas separadas?"),
    ("8.7","Control de Plagas","My","10.12","¿Se cuenta con un programa escrito de control de plagas y roedores?"),
    ("9.1","Adaptación de Animales","My","11.1.1","¿Se realiza un proceso de adaptación para animales introducidos?"),
    ("9.2","Superficies y Espacio","My","11.1.2","¿Las superficies (potreros) permiten un desplazamiento seguro?"),
    ("9.3","Agrupamiento Social","My","11.1.3","¿Se permite el agrupamiento social sin causar lesiones?"),
    ("9.4","Estabulación","My","11.1.4","¿En estabulación, la ventilación y temperatura son adecuadas?"),
    ("9.5","Enfermedades y Parásitos","My","11.1.6","¿Se controlan y tratan oportunamente las enfermedades?"),
    ("9.6","Alimentos y Agua","My","11.1.5","¿Los animales tienen acceso suficiente a alimentos y agua?"),
    ("9.7","Sacrificio Humanitario","My","11.1.6","¿Cuando es necesario, se aplica sacrificio humanitario?"),
    ("9.8","Manejo del Dolor","F","11.1.7","¿En procedimientos dolorosos se maneja el dolor en los animales?"),
    ("9.9","Relación Hombre-Animal","My","11.1.8","¿El manejo promueve una relación positiva sin causar estrés?"),
    ("10.1","Capacitación del Personal","F","11.2.1","¿El personal cuenta con capacitación en buenas prácticas ganaderas?"),
    ("10.2","Uso de Implementos","Mn","11.2.1","¿El personal hace uso de los implementos necesarios?"),
]

sheet_title = "Criterios - Referencia"

# Get the new sheet ID
spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
new_sheet_id = None
for s in spreadsheet.get('sheets', []):
    if s['properties']['title'] == sheet_title:
        new_sheet_id = s['properties']['sheetId']
        break

if not new_sheet_id:
    print("ERROR: Sheet not found")
    exit(1)

# Write data: header + all criteria
all_rows = [["N°", "Nombre del Criterio", "Tipo", "Artículo", "Pregunta Exacta"]]
for num, nombre, tipo, art, pregunta in criterios:
    all_rows.append([num, nombre, tipo, art, pregunta])

body = {
    "valueInputOption": "RAW",
    "data": [{"range": f"'{sheet_title}'!A1:E{len(all_rows)}", "values": all_rows}]
}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print(f"✅ Datos escritos: {len(all_rows)-1} criterios")

# Format everything with simple batch
requests = [
    # Header row styling
    {
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 5},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.18, "green": 0.33, "blue": 0.59},
                    "horizontalAlignment": "CENTER",
                    "wrapStrategy": "WRAP",
                    "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
                }
            },
            "fields": "userEnteredFormat"
        }
    },
]

# Color the Tipo column for each row
for i, (_, _, tipo, _, _) in enumerate(criterios, 2):
    if tipo == "F":
        bg = {"red": 0.95, "green": 0.72, "blue": 0.72}
    elif tipo == "My":
        bg = {"red": 1.0, "green": 0.85, "blue": 0.60}
    else:
        bg = {"red": 0.72, "green": 0.90, "blue": 0.72}
    
    requests.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": i-1, "endRowIndex": i, "startColumnIndex": 2, "endColumnIndex": 3},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": bg,
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"bold": True}
                }
            },
            "fields": "userEnteredFormat"
        }
    })

# Column widths
col_widths = [{"startIndex":0,"endIndex":1,"pixelSize":60},
              {"startIndex":1,"endIndex":2,"pixelSize":280},
              {"startIndex":2,"endIndex":3,"pixelSize":65},
              {"startIndex":3,"endIndex":4,"pixelSize":130},
              {"startIndex":4,"endIndex":5,"pixelSize":600}]
for cw in col_widths:
    requests.append({
        "updateDimensionProperties": {
            "range": {"sheetId": new_sheet_id, "dimension": "COLUMNS", "startIndex": cw["startIndex"], "endIndex": cw["endIndex"]},
            "properties": {"pixelSize": cw["pixelSize"]},
            "fields": "pixelSize"
        }
    })

# Freeze header row
requests.append({
    "updateSheetProperties": {
        "properties": {"sheetId": new_sheet_id, "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount"
    }
})

# Execute in one batch
body = {"requests": requests}
response = service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print(f"✅ Formato aplicado: {len(response.get('replies', []))} respuestas")
print(f"\n✅ Hoja '{sheet_title}' completada exitosamente!")
