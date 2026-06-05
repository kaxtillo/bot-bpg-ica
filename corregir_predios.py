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

# Get current data to see what's in each column
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='A2:P3'
).execute()
values = result.get('values', [])

print("=== READING AGAIN FOR DEBUG ===")
for i, row in enumerate(values):
    for j, val in enumerate(row):
        print(f"  Row {i+2}, Col {j+1}: '{val}'")

# The latitude column (col J=10) has dots as thousand separators
# We need to write clean values
