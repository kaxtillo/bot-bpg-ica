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

# Criterio 7.3 está en la posición 33 (0-indexed) de los 62 criterios
# Columnas base = 16 (A-P), criterios empiezan en col 17 (Q) 
# 7.3 = index 33 dentro de criterios -> columna 16 + 33 = 49
# Criterios: 1.1(idx0) ... 7.3 es el 34º criterio (idx 33 de 0 a 61)
# Columnas: Q=col17+R3... 
# col 17 + 33 = col 50 -> AX

# Let's confirm the exact column for 7.3
# Índices de criterios:
# Sec 1 (1.1-1.7): indices 0-6
# Sec 2 (2.1-2.2): indices 7-8
# Sec 3 (3.1-3.5): indices 9-13
# Sec 4 (4.1-4.9): indices 14-22
# Sec 5 (5.1-5.2): indices 23-24
# Sec 6 (6.1-6.12): indices 25-36
# Sec 7 (7.1-7.7): indices 37-43
#   7.1=idx37, 7.2=idx38, 7.3=idx39

crit_col_index = 16 + 39  # = col 55

def col_to_letter(n):
    result = ""
    while n > 0:
        n -= 1
        result = chr(ord('A') + n % 26) + result
        n //= 26
    return result

col_letter = col_to_letter(crit_col_index + 1)  # +1 because 1-indexed
print(f"Criterio 7.3 está en columna: {col_letter}{col_letter}")

# Actually let's just write to the right cell
# 16 base columns + 39 = 55th column, 1-indexed
# col 55: 26 -> Z, 52 -> AZ, 55 -> BC
print(f"Número de columna: {55}")
print(f"Letra: {col_to_letter(55)}")

# Write SI to the cell
body = {
    "valueInputOption": "RAW",
    "data": [{"range": f"Hoja 1!BC3", "values": [["SI"]]}]
}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print("✅ Criterio 7.3 cambiado a SI")

# Now recalculate results
# Get all criteria for row 3
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='Q3:BZ3'
).execute()
vals = result.get('values', [[]])[0]
print(f"\nValores criterios: {vals}")

# Tipos
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

f_total = tipos.count("F")
my_total = tipos.count("My")
mn_total = tipos.count("Mn")

f_cumpl = sum(1 for r, t in zip(vals, tipos) if r == "SI" and t == "F")
my_cumpl = sum(1 for r, t in zip(vals, tipos) if r == "SI" and t == "My")
mn_cumpl = sum(1 for r, t in zip(vals, tipos) if r == "SI" and t == "Mn")

f_pct = round((f_cumpl / f_total) * 100, 1)
my_pct = round((my_cumpl / my_total) * 100, 1)
mn_pct = round((mn_cumpl / mn_total) * 100, 1)

print(f"\n=== RESULTADOS ACTUALIZADOS SAN JOSÉ 5 ===")
print(f"Fundamentales: {f_cumpl}/{f_total} = {f_pct}% (min 90%)")
print(f"Mayores: {my_cumpl}/{my_total} = {my_pct}% (min 80%)")
print(f"Menores: {mn_cumpl}/{mn_total} = {mn_pct}% (min 70%)")

concepto = "Certificable" if (f_pct >= 90 and my_pct >= 80 and mn_pct >= 70) else "Aplazado"
print(f"Concepto: {concepto}")

if concepto == "Certificable":
    observacion = "El predio cumple con los umbrales mínimos de la Resolución 067449 para certificación BPG."
    recomendacion = "Mantener la documentación actualizada y corregir los criterios con NO pendientes."
else:
    observacion = f"No cumple umbrales. F:{f_pct}%(min 90%), My:{my_pct}%(min 80%), Mn:{mn_pct}%(min 70%)"
    recomendacion = "Priorizar: 1) Certificación hatos libres (Art 5.1.2), 2) Prescripción veterinaria (Art 8.9/8.15)"

# Update results in sheet
result_values = [str(f_cumpl), str(f_total), str(f_pct), str(my_cumpl), str(my_total), str(my_pct), 
                 str(mn_cumpl), str(mn_total), str(mn_pct), concepto, observacion, recomendacion]
body = {
    "valueInputOption": "RAW",
    "data": [{"range": "Hoja 1!CA3:CL3", "values": [result_values]}]
}
service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
print("✅ Resultados recalculados y guardados en hoja")
