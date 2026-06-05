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
    client_id='675307706784-857u244apvcaef30esvbfmduqikeg0a3.apps.googleusercontent.com',
    client_secret='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',
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

