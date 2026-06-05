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

# Read all headers on row 1
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='1:1'
).execute()
headers = result.get('values', [[]])[0]

# Find the column header for C7.3
for i, h in enumerate(headers):
    if "7.3" in h or "7.3|F" in h:
        print(f"C7.3 found at column {i+1} (letter: {chr(64+i+1) if i+1<=26 else '??'}): '{h}'")
        
def col_to_letter(n):
    result = ""
    while n > 0:
        n -= 1
        result = chr(ord('A') + n % 26) + result
        n //= 26
    return result

# Get the actual value at that position
for i, h in enumerate(headers):
    if "7.3" in h:
        col_letter = col_to_letter(i + 1)
        cell_val = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=f"Hoja 1!{col_letter}3"
        ).execute()
        val = cell_val.get('values', [[None]])[0][0]
        print(f"Value at {col_letter}3 (col {i+1}): {val}")
        
        # Also write it directly
        body = {"valueInputOption": "RAW", "data": [{"range": f"Hoja 1!{col_letter}3", "values": [["SI"]]}]}
        service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
        print(f"  ✅ Forzado SI en {col_letter}3")
        break

# Recount
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='Q3:BZ3'
).execute()
vals = result.get('values', [[]])[0]

tipos = [
    "F","My","F","F","F","F","F",
    "F","My",
    "My","My","My","Mn","Mn",
    "My","F","F","Mn","F","F","F","My","My",
    "F","My",
    "F","F","My","F","F","F","F","F","F","My","My","My","My",
    "F","F","F","My","F","Mn","My",
    "My","My","My","My","My","My","My",
    "My","My","My","My","My","My","My","F","My",
    "F","Mn"
]

# Find all NO values
print("\n=== CRITERIOS CON NO ===")
crit_names = [
    "1.1","1.2","1.3","1.4","1.5","1.6","1.7",
    "2.1","2.2",
    "3.1","3.2","3.3","3.4","3.5",
    "4.1","4.2","4.3","4.4","4.5","4.6","4.7","4.8","4.9",
    "5.1","5.2",
    "6.1","6.2","6.3","6.4","6.5","6.6","6.7","6.8","6.9","6.10","6.11","6.12",
    "7.1","7.2","7.3","7.4","7.5","7.6","7.7",
    "8.1","8.2","8.3","8.4","8.5","8.6","8.7",
    "9.1","9.2","9.3","9.4","9.5","9.6","9.7","9.8","9.9",
    "10.1","10.2"
]
for i, (v, t, n) in enumerate(zip(vals, tipos, crit_names)):
    if v == "NO":
        print(f"  {n} ({t}): NO ❌")

f_total = tipos.count("F")
my_total = tipos.count("My")
mn_total = tipos.count("Mn")
f_cumpl = sum(1 for r, t in zip(vals, tipos) if r == "SI" and t == "F")
my_cumpl = sum(1 for r, t in zip(vals, tipos) if r == "SI" and t == "My")
mn_cumpl = sum(1 for r, t in zip(vals, tipos) if r == "SI" and t == "Mn")

f_pct = round((f_cumpl / f_total) * 100, 1)
my_pct = round((my_cumpl / my_total) * 100, 1)
mn_pct = round((mn_cumpl / mn_total) * 100, 1)

print(f"\n=== RESULTADOS FINALES ===")
print(f"F: {f_cumpl}/{f_total} = {f_pct}%")
print(f"My: {my_cumpl}/{my_total} = {my_pct}%")
print(f"Mn: {mn_cumpl}/{mn_total} = {mn_pct}%")

concepto = "Certificable" if (f_pct >= 90 and my_pct >= 80 and mn_pct >= 70) else "Aplazado"
print(f"Concepto: {concepto}")

if concepto == "Certificable":
    obs = "El predio cumple con los umbrales mínimos de la Resolución 067449 para certificación BPG."
    rec = "Mantener la documentación actualizada y corregir los criterios con NO pendientes."
else:
    obs = f"No cumple umbrales. F:{f_pct}%(min 90%), My:{my_pct}%(min 80%), Mn:{mn_pct}%(min 70%)"
    rec = "Priorizar: 1) Certificación hatos libres (Art 5.1.2), 2) Prescripción veterinaria (Art 8.9/8.15)"

res_vals = [str(f_cumpl), str(f_total), str(f_pct), str(my_cumpl), str(my_total), str(my_pct), 
             str(mn_cumpl), str(mn_total), str(mn_pct), concepto, obs, rec]
body = {"valueInputOption": "RAW", "data": [{"range": "Hoja 1!CA3:CL3", "values": [res_vals]}]}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print("✅ Resultados finales guardados")
