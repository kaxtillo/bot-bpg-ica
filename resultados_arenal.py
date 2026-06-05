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

# Respuestas EL ARENAL (Row 2)
respuestas = [
    "SI","NO","SI","SI","SI","SI","SI",  # 1.1-1.7
    "SI","SI",                            # 2.1-2.2
    "SI","SI","SI","NA","SI",             # 3.1-3.5
    "NA","NO","SI","SI","SI","SI","SI","SI","SI",  # 4.1-4.9
    "NA","NA",                            # 5.1-5.2
    "SI","SI","SI","SI","SI","SI","SI","SI","SI","SI","SI","SI",  # 6.1-6.12
    "SI","NA","NA","NA","SI","SI","NA",   # 7.1-7.7
    "SI","SI","SI","SI","SI","SI","SI",  # 8.1-8.7
    "NA","SI","SI","NA","SI","SI","SI","SI","SI",  # 9.1-9.9
    "SI","SI"                             # 10.1-10.2
]

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

# Write criteria to row 2
def col_to_letter(n):
    result = ""
    while n > 0:
        n -= 1
        result = chr(ord('A') + n % 26) + result
        n //= 26
    return result

crit_start = col_to_letter(17)  # Q
crit_end = col_to_letter(17 + 62 - 1)  # BZ
crit_range = f"Hoja 1!{crit_start}2:{crit_end}2"

body = {"valueInputOption": "RAW", "data": [{"range": crit_range, "values": [respuestas]}]}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print("✅ Criterios escritos en fila 2")

# Cálculo con NA excluido del denominador
def calc(tipo):
    relevant = [(r, t) for r, t in zip(respuestas, tipos) if t == tipo and r != "NA"]
    total = len(relevant)
    cumplidos = sum(1 for r, _ in relevant if r == "SI")
    pct = round((cumplidos / total) * 100, 1) if total > 0 else 0
    return cumplidos, total, pct

f_cumpl, f_total, f_pct = calc("F")
my_cumpl, my_total, my_pct = calc("My")
mn_cumpl, mn_total, mn_pct = calc("Mn")

print(f"\n=== RESULTADOS EL ARENAL ===")
print(f"Fundamentales: {f_cumpl}/{f_total} = {f_pct}% (min 90%)")
print(f"Mayores: {my_cumpl}/{my_total} = {my_pct}% (min 80%)")
print(f"Menores: {mn_cumpl}/{mn_total} = {mn_pct}% (min 70%)")

concepto = "Certificable" if (f_pct >= 90 and my_pct >= 80 and mn_pct >= 70) else "Aplazado"
print(f"Concepto: {concepto}")

# List NOs
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
nos = [(n, t) for n, r, t in zip(crit_names, respuestas, tipos) if r == "NO"]
print(f"\nCriterios NO ({len(nos)}):")
for n, t in nos:
    print(f"  {n} ({t})")

obs = ""
rec = ""
if concepto == "Certificable":
    obs = "El predio cumple con los umbrales mínimos de la Resolución 067449 para certificación BPG."
    rec = "Corregir los criterios con NO para mejorar el puntaje general."
else:
    obs = f"No cumple umbrales. F:{f_pct}%(min 90%), My:{my_pct}%(min 80%), Mn:{mn_pct}%(min 70%). NA excluidos del denominador."
    rec = "Priorizar corrección de criterios Fundamentales y Mayores con NO."

result_values = [str(f_cumpl), str(f_total), str(f_pct), str(my_cumpl), str(my_total), str(my_pct), 
                 str(mn_cumpl), str(mn_total), str(mn_pct), concepto, obs, rec]
body = {"valueInputOption": "RAW", "data": [{"range": "Hoja 1!CA2:CL2", "values": [result_values]}]}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print("\n✅ Resultados guardados en hoja")
