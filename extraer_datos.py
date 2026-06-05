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

# Get all data from both rows
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='A2:AB1000'
).execute()
values = result.get('values', [])

print("=== DATOS COMPLETOS DE PREDIOS ===")
for i, row in enumerate(values):
    print(f"\n--- PREDIO (Row {i+2}) ---")
    campos = ["Fecha","Propietario","Identificación","Teléfono","Email","Predio",
              "Departamento","Municipio","Vereda","Latitud","Longitud","RSPP",
              "Especie","FinZootécnico","Producción","TotalAnimales",
              "FCumplidos","FTotal","FPorcentaje","MyCumplidos","MyTotal","MyPorcentaje",
              "MnCumplidos","MnTotal","MnPorcentaje","Concepto","Observación","Recomendación"]
    for j, campo in enumerate(campos):
        if j < len(row):
            val = row[j].strip() if row[j] else ""
            if val:
                print(f"  {campo}: {val}")
