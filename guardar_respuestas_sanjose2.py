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

# Respuestas SAN JOSÉ 5 (Row 3)
respuestas = [
    "SI","NO","SI","SI","SI","SI","SI",  # 1.1-1.7
    "SI","SI",                            # 2.1-2.2
    "SI","SI","SI","NA","SI",             # 3.1-3.5
    "NA","NA","SI","SI","SI","SI","SI","SI","SI",  # 4.1-4.9
    "NA","NA",                            # 5.1-5.2
    "SI","SI","SI","NA","NA","SI","NO","SI","SI","SI","SI","SI",  # 6.1-6.12
    "SI","NA","NO","NA","SI","SI","NA",   # 7.1-7.7
    "SI","SI","SI","SI","SI","SI","SI",  # 8.1-8.7
    "SI","SI","SI","NA","SI","SI","SI","SI","SI",  # 9.1-9.9
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
    observacion = f"No cumple umbrales. F:{f_pct}%(≥90%), My:{my_pct}%(≥80%), Mn:{mn_pct}%(≥70%)"
    recomendacion = "Revisar: Certificación hatos libres (1.2), Prescripción veterinaria (6.7), Prohibiciones alimentarias (7.3)."

# Use A1 notation: criteria start at column Q (17) = col 17
# Write criteria values
criteria_range = f"Hoja 1!Q3:{chr(ord('A') + 17 + len(respuestas) - 1)}3"

body = {
    "valueInputOption": "RAW",
    "data": [{"range": criteria_range, "values": [respuestas]}]
}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print("✅ Criterios escritos")

# Wait, 17 + 62 = 79. Column 79 in A1 notation:
# 1-26: A-Z, 27-52: AA-AZ, 53-78: BA-BZ, 79: CA
# Columns: Q(17) to CA(79)
criteria_end_letter = "CA"
criteria_range2 = f"Hoja 1!Q3:{criteria_end_letter}3"
body = {
    "valueInputOption": "RAW",
    "data": [{"range": criteria_range2, "values": [respuestas]}]
}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print("✅ Criterios escritos (range: Q3:CA3)")

# Results start at column 79 (CA) = index 78 in 0-based but 79 in 1-based
# CA3:CL3 (79 to 90)
result_values = [str(f_cumpl), str(f_total), str(f_pct), str(my_cumpl), str(my_total), str(my_pct), 
                 str(mn_cumpl), str(mn_total), str(mn_pct), concepto, observacion, recomendacion]
result_range = "Hoja 1!CA3:CL3"
body = {
    "valueInputOption": "RAW",
    "data": [{"range": result_range, "values": [result_values]}]
}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print("✅ Resultados escritos en CA3:CL3")

# Verify everything
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='Q3:CL3'
).execute()
vals = result.get('values', [[]])[0]
print(f"\n✅ Verificación - Total {len(vals)} valores escritos en fila 3")
print(f"   Primer criterio (Q3): {vals[0]}")
print(f"   Último criterio: {vals[61]}")
print(f"   FCumplidos: {vals[62]}")
print(f"   Concepto: {vals[70]}")
