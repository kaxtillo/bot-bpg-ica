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

# Get all data
result = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range='A2:CL100').execute()
rows = result.get('values', [])

print("=== LISTADO DE PREDIOS EN BASE DE DATOS ===\n")
for i, row in enumerate(rows):
    if not row or len(row) < 6:
        continue
    fecha = row[0] if len(row) > 0 and row[0] else ""
    propietario = row[1] if len(row) > 1 and row[1] else ""
    identificacion = row[2] if len(row) > 2 and row[2] else ""
    telefono = row[3] if len(row) > 3 and row[3] else ""
    predio = row[5] if len(row) > 5 and row[5] else ""
    depto = row[6] if len(row) > 6 and row[6] else ""
    municipio = row[7] if len(row) > 7 and row[7] else ""
    vereda = row[8] if len(row) > 8 and row[8] else ""
    especie = row[12] if len(row) > 12 and row[12] else ""
    fin = row[13] if len(row) > 13 and row[13] else ""
    produccion = row[14] if len(row) > 14 and row[14] else ""
    animales = row[15] if len(row) > 15 and row[15] else ""
    
    # Resultados si existen
    concepto = ""
    if len(row) > 77:  # Tiene más de 78 columnas
        f_c = row[78] if len(row) > 78 and row[78] else ""
        f_t = row[79] if len(row) > 79 and row[79] else ""
        f_p = row[80] if len(row) > 80 and row[80] else ""
        my_c = row[81] if len(row) > 81 and row[81] else ""
        my_t = row[82] if len(row) > 82 and row[82] else ""
        my_p = row[83] if len(row) > 83 and row[83] else ""
        mn_c = row[84] if len(row) > 84 and row[84] else ""
        mn_t = row[85] if len(row) > 85 and row[85] else ""
        mn_p = row[86] if len(row) > 86 and row[86] else ""
        concepto = row[87] if len(row) > 87 and row[87] else ""
        
        print(f"📋 Predio #{i+2}")
        print(f"   Nombre: {predio}")
        print(f"   Propietario: {propietario} ({identificacion})")
        print(f"   Ubicación: {municipio}/{depto} - Vereda {vereda}")
        print(f"   Contacto: {telefono}")
        print(f"   Producción: {especie} - {fin} - {produccion} L - {animales} animales")
        if concepto:
            print(f"   Resultado: F {f_c}/{f_t} ({f_p}%) | My {my_c}/{my_t} ({my_p}%) | Mn {mn_c}/{mn_t} ({mn_p}%)")
            print(f"   Concepto: {concepto}")
        print()

print(f"Total: {len(rows)} predios registrados")
