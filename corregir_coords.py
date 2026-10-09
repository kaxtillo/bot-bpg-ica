def _gcred(campo, por_defecto=""):
    """Credencial de Google leída de ~/.hermes/google_token.json (NUNCA del código).

    Los secretos no van en el repositorio: se leen en tiempo de ejecución del archivo
    de token, que vive fuera del repo y no se publica.
    """
    import json as _json, os as _os
    try:
        with open(_os.path.expanduser("~/.hermes/google_token.json")) as f:
            return _json.load(f).get(campo, por_defecto)
    except Exception:
        return por_defecto

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
    client_id=_gcred('client_id'),
    client_secret=_gcred('client_secret'),
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

service = build('sheets', 'v4', credentials=creds)

# Just fix coordinates with proper numbers
# We write them as strings that Google Sheets can parse
body = {
    "valueInputOption": "USER_ENTERED",
    "data": [
        # Row 2: fix lat/lng to proper numbers  
        {"range": "J2", "values": [["2.454843"]]},
        {"range": "K2", "values": [["-76.631613"]]},
        # Row 3: fix lat/lng
        {"range": "J3", "values": [["2.241723"]]},
        {"range": "K3", "values": [["-76.554590"]]},
    ]
}

response = service.spreadsheets().values().batchUpdate(
    spreadsheetId=SHEET_ID, body=body
).execute()
print("✅ Coordenadas corregidas")

# Verify  
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='A3:P3'
).execute()
row = result.get('values', [[]])[0]
print(f"Row 3 actualizado: Lat={row[9]}, Lng={row[10]}")
