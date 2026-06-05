import pickle, os, json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = '1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg'
creds_file = '/home/ubuntu/.openclaw/workspace/token.pickle'
creds_json = '/home/ubuntu/.openclaw/workspace/credentials.json'

creds = None
if os.path.exists(creds_file):
    with open(creds_file, 'rb') as f:
        creds = pickle.load(f)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(creds_json, SCOPES)
        creds = flow.run_local_server(port=0, open_browser=False)
    with open(creds_file, 'wb') as f:
        pickle.dump(creds, f)

service = build('sheets', 'v4', credentials=creds)

# Get existing sheet metadata
sheet_meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
print("Sheet name:", sheet_meta['properties']['title'])
for s in sheet_meta.get('sheets', []):
    print(f"  Sheet: {s['properties']['title']} (rows={s['properties'].get('gridProperties',{}).get('rowCount','?')}, cols={s['properties'].get('gridProperties',{}).get('columnCount','?')})")

# Get existing headers to see current structure
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID,
    range='1:1'
).execute()
headers = result.get('values', [[]])[0]
print(f"\nCurrent headers ({len(headers)}):")
for i, h in enumerate(headers):
    print(f"  Col {i+1}: {h}")
