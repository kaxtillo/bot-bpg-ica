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

def col_to_letter(n):
    result = ""
    while n > 0:
        n -= 1
        result = chr(ord('A') + n % 26) + result
        n //= 26
    return result

# First find next empty row
result = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range='A:A').execute()
values = result.get('values', [])
next_row = len(values) + 1
print(f"Next row: {next_row}")

# Datos base SANTA BÁRBARA
base = ["2026-05-03", "Leonel Sosa", "76216387", "", "", "Santa Bárbara", "Cauca", "Cajibío", "Cairo",
        "2.60750", "-76.55906", "", "Bovina", "Leche", "540", "60"]

# Respuestas
respuestas = [
    "SI","NO","SI","SI","NO","SI","NO",  # 1.1-1.7
    "SI","SI",                            # 2.1-2.2
    "SI","NO","NO","SI","SI",             # 3.1-3.5
    "SI","SI","NA","SI","SI","SI","NO","SI","SI",  # 4.1-4.9
    "SI","NO",                            # 5.1-5.2
    "SI","SI","SI","SI","NO","SI","SI","SI","SI","NO","SI","SI",  # 6.1-6.12
    "SI","NA","SI","NA","SI","SI","SI",   # 7.1-7.7
    "SI","SI","SI","SI","NO","SI","NO",  # 8.1-8.7
    "SI","SI","SI","NA","SI","SI","SI","SI","SI",  # 9.1-9.9
    "NO","SI"                             # 10.1-10.2
]

tipos = ["F","My","F","F","F","F","F","F","My","My","My","My","Mn","Mn","My","F","F","Mn","F","F","F","My","My","F","My",
         "F","F","My","F","F","F","F","F","F","My","My","My","My","F","F","F","My","F","Mn","My",
         "My","My","My","My","My","My","My","My","My","My","My","My","My","F","My","F","Mn"]

# Calcular con NA excluido
def calc(tipo):
    relevant = [(r, t) for r, t in zip(respuestas, tipos) if t == tipo and r != "NA"]
    total = len(relevant)
    cumplidos = sum(1 for r, _ in relevant if r == "SI")
    pct = round((cumplidos / total) * 100, 1) if total > 0 else 0
    return cumplidos, total, pct

f_cumpl, f_total, f_pct = calc("F")
my_cumpl, my_total, my_pct = calc("My")
mn_cumpl, mn_total, mn_pct = calc("Mn")

concepto = "Certificable" if (f_pct >= 90 and my_pct >= 80 and mn_pct >= 70) else "Aplazado"

# Write row
row_data = base + respuestas + [str(f_cumpl),str(f_total),str(f_pct),str(my_cumpl),str(my_total),str(my_pct),
                                 str(mn_cumpl),str(mn_total),str(mn_pct), concepto, "", ""]

crit_start = col_to_letter(17)
crit_end = col_to_letter(17 + 62 - 1)
range_str = f"Hoja 1!A{next_row}:CL{next_row}"

body = {"valueInputOption": "RAW", "data": [{"range": range_str, "values": [row_data]}]}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()

print(f"\n=== RESULTADOS SANTA BÁRBARA ===")
print(f"Fundamentales: {f_cumpl}/{f_total} = {f_pct}% (min 90%) {'✅' if f_pct>=90 else '❌'}")
print(f"Mayores: {my_cumpl}/{my_total} = {my_pct}% (min 80%) {'✅' if my_pct>=80 else '❌'}")
print(f"Menores: {mn_cumpl}/{mn_total} = {mn_pct}% (min 70%) {'✅' if mn_pct>=70 else '❌'}")
print(f"Concepto: {concepto}")
print(f"✅ Datos guardados en fila {next_row}")
