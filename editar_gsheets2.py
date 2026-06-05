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

# Criterios en orden
criterios = [
    ("1.1", "Plan Sanitario", "F", "5.1.1"),
    ("1.2", "Certificación de Hatos Libres", "My", "5.1.2"),
    ("1.3", "Protocolo de Aislamiento", "F", "5.1.3"),
    ("1.4", "Registro de Diagnósticos", "F", "5.1.4"),
    ("1.5", "Instructivo de Enfermedades", "F", "5.1.5"),
    ("1.6", "Área de Enfermería", "F", "5.1.6"),
    ("1.7", "Programa de Mastitis", "F", "5.1.7"),
    ("2.1", "Identificación de Animales", "F", "5.2.1"),
    ("2.2", "Registro Individual", "My", "5.2.2"),
    ("3.1", "Delimitación del Predio", "My", "5.3.1"),
    ("3.2", "Registro de Visitas", "My", "5.3.2"),
    ("3.3", "Cuarentena", "My", "5.3.3"),
    ("3.4", "Material Genético", "Mn", "5.3.4"),
    ("3.5", "Identificación de Áreas", "Mn", "5.3.5"),
    ("4.1", "Zona de Espera", "My", "6.1"),
    ("4.2", "Instalaciones de Ordeño Fijo", "F", "6.2"),
    ("4.3", "Instalaciones de Ordeño Móvil", "F", "6.3"),
    ("4.4", "Instalaciones Sanitarias", "Mn", "6.4"),
    ("4.5", "Rutina de Ordeño", "F", "6.5.1"),
    ("4.6", "Equipos y Utensilios", "F", "6.5.2"),
    ("4.7", "Disposición Leche Anormal", "F", "6.5.4"),
    ("4.8", "Agua para Ordeño", "My", "6.5.5"),
    ("4.9", "Conservación de la Leche", "My", "6.5.7"),
    ("5.1", "Cuarto del Tanque de Leche", "F", "7.1"),
    ("5.2", "Registro de Temperatura", "My", "7.5"),
    ("6.1", "Productos con Registro ICA", "F", "8.1"),
    ("6.2", "Productos No Vencidos", "F", "8.2"),
    ("6.3", "Almacenamiento de Medicamentos", "My", "8.3"),
    ("6.4", "Sustancias Prohibidas", "F", "8.6"),
    ("6.5", "Materias Primas como Medicamentos", "F", "8.7"),
    ("6.6", "Tiempos de Retiro", "F", "8.8"),
    ("6.7", "Prescripción Veterinaria", "F", "8.9"),
    ("6.8", "Registros de Tratamientos", "F", "8.10"),
    ("6.9", "Equipos de Administración", "My", "8.11"),
    ("6.10", "Inventario de Productos", "My", "8.13"),
    ("6.11", "Autorización para Aplicación", "My", "8.14"),
    ("6.12", "Notificación de Eventos Adversos", "My", "8.16"),
    ("7.1", "Alimentos con Registro ICA", "F", "9.1"),
    ("7.2", "Alimento Medicado", "F", "9.2"),
    ("7.3", "Prohibiciones Alimentarias", "F", "9.6"),
    ("7.4", "Subproductos", "My", "9.4"),
    ("7.5", "Insumos Agrícolas", "F", "9.8"),
    ("7.6", "Inventario de Alimentos", "Mn", "9.10"),
    ("7.7", "Calidad del Agua", "My", "9.11"),
    ("8.1", "Limpieza de Áreas", "My", "10.1"),
    ("8.2", "Ubicación del Predio", "My", "10.2"),
    ("8.3", "Protección de Fuentes Hídricas", "My", "10.3"),
    ("8.4", "Disposición de Estiércol", "My", "10.5"),
    ("8.5", "Manejo de Residuos", "My", "10.6"),
    ("8.6", "Almacenamiento de Insumos", "My", "10.9"),
    ("8.7", "Control de Plagas", "My", "10.12"),
    ("9.1", "Adaptación de Animales", "My", "11.1.1"),
    ("9.2", "Superficies y Espacio", "My", "11.1.2"),
    ("9.3", "Agrupamiento Social", "My", "11.1.3"),
    ("9.4", "Estabulación", "My", "11.1.4"),
    ("9.5", "Enfermedades y Parásitos", "My", "11.1.6"),
    ("9.6", "Alimentos y Agua", "My", "11.1.5"),
    ("9.7", "Sacrificio Humanitario", "My", "11.1.6"),
    ("9.8", "Manejo del Dolor", "F", "11.1.7"),
    ("9.9", "Relación Hombre-Animal", "My", "11.1.8"),
    ("10.1", "Capacitación del Personal", "F", "11.2.1"),
    ("10.2", "Uso de Implementos", "Mn", "11.2.1"),
]

# Build new header row
base_headers = ["Fecha", "Propietario", "Identificación", "Teléfono", "Email",
    "Predio", "Departamento", "Municipio", "Vereda", "Latitud", "Longitud",
    "RSPP", "Especie", "FinZootécnico", "Producción", "TotalAnimales"]

crit_headers = []
for num, nombre, tipo, art in criterios:
    crit_headers.append(f"C{num}|{tipo}")

result_headers = ["FCumplidos", "FTotal", "FPorcentaje",
    "MyCumplidos", "MyTotal", "MyPorcentaje",
    "MnCumplidos", "MnTotal", "MnPorcentaje",
    "Concepto", "Observación", "Recomendación"]

new_headers = base_headers + crit_headers + result_headers
print(f"Total new headers: {len(new_headers)}")

# Step 1: First, expand columns from 28 to 90
# We need to insert 62 columns at position 17 (after TotalAnimales)
requests = []

# Insert 62 blank columns starting at column Q (17)
requests.append({
    "insertDimension": {
        "range": {
            "sheetId": 0,
            "dimension": "COLUMNS",
            "startIndex": 16,  # 0-indexed, after TotalAnimales at index 15
            "endIndex": 78     # insert 62 columns
        },
        "inheritFromBefore": False
    }
})

# Write the new header row
requests.append({
    "updateCells": {
        "range": {
            "sheetId": 0,
            "startRowIndex": 0,
            "endRowIndex": 1,
            "startColumnIndex": 0,
            "endColumnIndex": len(new_headers)
        },
        "rows": [{"values": [{"userEnteredValue": {"stringValue": h}} for h in new_headers]}],
        "fields": "userEnteredValue"
    }
})

# Step 3: Add data validation (dropdown) for criterion columns
# Col indices in new sheet (0-indexed): criteria start at 16, end at 77
for i in range(16, 78):
    col_letter = chr(ord('A') + i) if i < 26 else chr(ord('A') + (i//26) - 1) + chr(ord('A') + (i%26))
    # Actually Google Sheets API uses numeric columns, so let's add validation via setDataValidation
    requests.append({
        "setDataValidation": {
            "range": {
                "sheetId": 0,
                "startRowIndex": 1,
                "endRowIndex": 1000,
                "startColumnIndex": i,
                "endColumnIndex": i + 1
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [
                        {"userEnteredValue": "SI"},
                        {"userEnteredValue": "NO"},
                        {"userEnteredValue": "NA"}
                    ]
                },
                "strict": True,
                "showCustomUi": True
            }
        }
    })

# Add validation for Concepto column (index 88)
requests.append({
    "setDataValidation": {
        "range": {
            "sheetId": 0,
            "startRowIndex": 1,
            "endRowIndex": 1000,
            "startColumnIndex": 87,
            "endColumnIndex": 88
        },
        "rule": {
            "condition": {
                "type": "ONE_OF_LIST",
                "values": [
                    {"userEnteredValue": "Certificable"},
                    {"userEnteredValue": "Aplazado"}
                ]
            },
            "strict": True,
            "showCustomUi": True
        }
    }
})

# Execute in batches
batch_size = 100
for i in range(0, len(requests), batch_size):
    batch = requests[i:i+batch_size]
    body = {"requests": batch}
    response = service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
    print(f"Batch {i//batch_size + 1}: {len(batch)} requests - OK")
    print(f"  Replies: {len(response.get('replies', []))}")

print("\n✅ Spreadsheet updated successfully!")

# Verify new structure
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='1:1'
).execute()
new_headers_actual = result.get('values', [[]])[0]
print(f"\nFinal headers count: {len(new_headers_actual)}")
print(f"First 5: {new_headers_actual[:5]}")
print(f"Criteria sample: {new_headers_actual[16:20]}")
print(f"Last 3: {new_headers_actual[-3:]}")
