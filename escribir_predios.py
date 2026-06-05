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

# Datos EL ARENAL
row2_base = [
    "2026-03-23", "Francy Quira", "25852698", "3258569987", "",
    "EL ARENAL", "Cauca", "Puracé", "Campamento",
    "2.454843", "-76.631613", "", "Bovina", "Leche", "500", "50"
]
# 62 blank criteria + 12 result columns
row2 = row2_base + [""] * 62 + [""] * 12

# Datos SAN JOSÉ 5
row3_base = [
    "2026-04-04", "Edison Lozada Mensa", "1064676804", "3105162252", "",
    "SAN JOSÉ 5", "Cauca", "Sotará", "Piedra de León",
    "2.241723", "-76.554590", "SI", "BOVINO LECHERO", "PRODUCCIÓN LECHE", "", ""
]
row3 = row3_base + [""] * 62 + [""] * 12

body = {
    "valueInputOption": "USER_ENTERED",
    "data": [
        {"range": "A2:CL2", "values": [row2]},
        {"range": "A3:CL3", "values": [row3]}
    ]
}

response = service.spreadsheets().values().batchUpdate(
    spreadsheetId=SHEET_ID, body=body
).execute()

print(f"✅ Filas actualizadas: {len(response.get('valueInputs', []))}")

# Verify
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='A2:R3'
).execute()
values = result.get('values', [])
for i, row in enumerate(values):
    print(f"\nRow {i+2}: {row}")
