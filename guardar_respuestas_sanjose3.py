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

def col_to_letter(n):
    """Convert 1-indexed column number to A1 notation (e.g., 1->A, 27->AA, 79->CA)"""
    result = ""
    while n > 0:
        n -= 1
        result = chr(ord('A') + n % 26) + result
        n //= 26
    return result

# Respuestas
respuestas = [
    "SI","NO","SI","SI","SI","SI","SI",
    "SI","SI",
    "SI","SI","SI","NA","SI",
    "NA","NA","SI","SI","SI","SI","SI","SI","SI",
    "NA","NA",
    "SI","SI","SI","NA","NA","SI","NO","SI","SI","SI","SI","SI",
    "SI","NA","NO","NA","SI","SI","NA",
    "SI","SI","SI","SI","SI","SI","SI",
    "SI","SI","SI","NA","SI","SI","SI","SI","SI",
    "SI","SI"
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

# Counts
f_total = tipos.count("F")
my_total = tipos.count("My")
mn_total = tipos.count("Mn")

f_cumpl = sum(1 for r, t in zip(respuestas, tipos) if r == "SI" and t == "F")
my_cumpl = sum(1 for r, t in zip(respuestas, tipos) if r == "SI" and t == "My")
mn_cumpl = sum(1 for r, t in zip(respuestas, tipos) if r == "SI" and t == "Mn")

f_pct = round((f_cumpl / f_total) * 100, 1)
my_pct = round((my_cumpl / my_total) * 100, 1)
mn_pct = round((mn_cumpl / mn_total) * 100, 1)

print(f"=== RESULTADOS SAN JOSÉ 5 ===")
print(f"Fundamentales: {f_cumpl}/{f_total} = {f_pct}%")
print(f"Mayores: {my_cumpl}/{my_total} = {my_pct}%")
print(f"Menores: {mn_cumpl}/{mn_total} = {mn_pct}%")

concepto = "Certificable" if (f_pct >= 90 and my_pct >= 80 and mn_pct >= 70) else "Aplazado"
print(f"Concepto: {concepto}")

if concepto == "Certificable":
    observacion = "El predio cumple con los umbrales mínimos de la Resolución 067449 para certificación BPG."
    recomendacion = "Mantener la documentación actualizada y corregir los criterios con NO."
else:
    observacion = f"No cumple umbrales. F:{f_pct}%(min 90%), My:{my_pct}%(min 80%), Mn:{mn_pct}%(min 70%)"
    recomendacion = "Priorizar: 1) Certificación hatos libres brucelosis/tuberculosis (Art 5.1.2), 2) Prescripción veterinaria (Art 8.9/8.15), 3) Prohibición harinas cárnicas (Art 9.6/9.7)"

# Criteria columns: 17 to 78 (0-indexed in sheet = 17-78)
# In A1: Q = col 17, CA = col 79
criteria_start = col_to_letter(17)  # Q
criteria_end = col_to_letter(17 + 62 - 1)  # CA
criteria_range = f"Hoja 1!{criteria_start}3:{criteria_end}3"
print(f"Writing criteria to: {criteria_range}")

body = {
    "valueInputOption": "RAW",
    "data": [{"range": criteria_range, "values": [respuestas]}]
}
response = service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print(f"✅ Criterios escritos ({len(response.get('valueInputs', []))} celdas)")

# Results columns: 79 to 90 (CA to CL)
result_start = col_to_letter(79)  # CA
result_end = col_to_letter(90)    # CL
result_range = f"Hoja 1!{result_start}3:{result_end}3"
print(f"Writing results to: {result_range}")

result_values = [str(f_cumpl), str(f_total), str(f_pct), str(my_cumpl), str(my_total), str(my_pct), 
                 str(mn_cumpl), str(mn_total), str(mn_pct), concepto, observacion, recomendacion]

body = {
    "valueInputOption": "RAW",
    "data": [{"range": result_range, "values": [result_values]}]
}
response = service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print(f"✅ Resultados escritos ({len(response.get('valueInputs', []))} celdas)")

# Quick verification
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='Q3:CL3'
).execute()
vals = result.get('values', [[]])[0]
print(f"\n✅ Verificación fila 3: {len(vals)} valores")
print(f"   Criterio 1.1 (Q3): {vals[0]}")
print(f"   Criterio 1.2 (R3): {vals[1]}")
print(f"   Criterio 6.7: {vals[26]}")  # index 26 = 1.1(0) + 6 = should be 6.7
print(f"   Criterio 7.3: {vals[32]}")
print(f"   Criterio 10.2 (último): {vals[61]}")
print(f"   FCumplidos: {vals[62]}")
print(f"   Concepto: {vals[70]}")
