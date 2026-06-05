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

# Find C6.7 in headers
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='1:1'
).execute()
headers = result.get('values', [[]])[0]

for i, h in enumerate(headers):
    if "6.7" in h:
        def col_to_letter(n):
            result = ""
            while n > 0:
                n -= 1
                result = chr(ord('A') + n % 26) + result
                n //= 26
            return result
        col_letter = col_to_letter(i + 1)
        print(f"C6.7 = col {i+1} ({col_letter}) -> header: '{h}'")
        
        # Write SI
        body = {"valueInputOption": "RAW", "data": [{"range": f"Hoja 1!{col_letter}3", "values": [["SI"]]}]}
        service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
        print(f"  ✅ SI escrito en {col_letter}3")
        
        # Verify
        val = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=f"Hoja 1!{col_letter}3").execute()
        print(f"  Verificado: {val.get('values',[['']])[0][0]}")
        break

# Recalculate results
result = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range='Q3:BZ3').execute()
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

f_cumpl = sum(1 for r, t in zip(vals, tipos) if r == "SI" and t == "F")
my_cumpl = sum(1 for r, t in zip(vals, tipos) if r == "SI" and t == "My")
mn_cumpl = sum(1 for r, t in zip(vals, tipos) if r == "SI" and t == "Mn")
f_total, my_total, mn_total = tipos.count("F"), tipos.count("My"), tipos.count("Mn")

f_pct = round((f_cumpl / f_total) * 100, 1)
my_pct = round((my_cumpl / my_total) * 100, 1)
mn_pct = round((mn_cumpl / mn_total) * 100, 1)

concepto = "Certificable" if (f_pct >= 90 and my_pct >= 80 and mn_pct >= 70) else "Aplazado"

if concepto == "Certificable":
    obs = "El predio cumple con los umbrales mínimos de la Resolución 067449 para certificación BPG."
    rec = "Mantener la documentación actualizada."
else:
    obs = f"No cumple umbrales. F:{f_pct}%(min 90%), My:{my_pct}%(min 80%), Mn:{mn_pct}%(min 70%)"
    rec = "Pendiente: Certificación hatos libres (Art 5.1.2)"

res_vals = [str(f_cumpl), str(f_total), str(f_pct), str(my_cumpl), str(my_total), str(my_pct), 
             str(mn_cumpl), str(mn_total), str(mn_pct), concepto, obs, rec]
body = {"valueInputOption": "RAW", "data": [{"range": "Hoja 1!CA3:CL3", "values": [res_vals]}]}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()

print(f"\n=== RESULTADOS ACTUALIZADOS ===")
print(f"F: {f_cumpl}/{f_total} = {f_pct}%")
print(f"My: {my_cumpl}/{my_total} = {my_pct}%")
print(f"Mn: {mn_cumpl}/{mn_total} = {mn_pct}%")
print(f"Concepto: {concepto}")
print("✅ Guardado en hoja")
