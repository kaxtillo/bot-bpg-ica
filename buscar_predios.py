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

# Get all data
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='A:A'
).execute()
fechas = result.get('values', [[], []])
print(f"Total rows with data: {len(fechas)}")

# Get column F (Predio)
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='F:F'
).execute()
predios = result.get('values', [])
print(f"\nAll predios found:")
for i, row in enumerate(predios):
    if i == 0: continue  # skip header
    if row:
        print(f"  Row {i+1}: {row[0]}")

# Also check for "ARENAL" or "SAN JOSE" with broader search
result_all = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='A1:Z1000'
).execute()
values = result_all.get('values', [])
print(f"\nSearching specific predios...")
for i, row in enumerate(values):
    if i == 0: continue
    predio_name = row[5].strip() if len(row) > 5 and row[5] else ""
    if "ARENAL" in predio_name.upper() or "SAN JOSE" in predio_name.upper() or "SAN JOSÉ" in predio_name.upper():
        fecha = row[0] if len(row) > 0 else ""
        prop = row[1] if len(row) > 1 else ""
        print(f"  Row {i+1}: Predio='{predio_name}' | Fecha={fecha} | Propietario={prop}")
