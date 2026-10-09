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

import json, os
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

# Get existing headers
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='1:1'
).execute()
headers = result.get('values', [[]])[0]
print(f"Current headers ({len(headers)}):")
for i, h in enumerate(headers):
    print(f"  Col {i+1}: {h}")

# Verify write access
result = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
print(f"\nSpreadsheet: {result['properties']['title']}")
sheets_info = result.get('sheets', [])
for s in sheets_info:
    props = s['properties']
    print(f"  Sheet: {props['title']} | Rows: {props.get('gridProperties',{}).get('rowCount')} | Cols: {props.get('gridProperties',{}).get('columnCount')}")

