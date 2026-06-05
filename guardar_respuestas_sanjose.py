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

# Respuestas SAN JOSÉ 5 (Row 3) - en orden estricto de los 62 criterios
respuestas = [
    "SI",   # 1.1 Plan Sanitario (F)
    "NO",   # 1.2 Certificación Hatos Libres (My)
    "SI",   # 1.3 Protocolo Aislamiento (F)
    "SI",   # 1.4 Registro Diagnósticos (F)
    "SI",   # 1.5 Instructivo Enfermedades (F)
    "SI",   # 1.6 Área Enfermería (F)
    "SI",   # 1.7 Programa Mastitis (F)
    "SI",   # 2.1 Identificación Animales (F)
    "SI",   # 2.2 Registro Individual (My)
    "SI",   # 3.1 Delimitación Predio (My)
    "SI",   # 3.2 Registro Visitas (My)
    "SI",   # 3.3 Cuarentena (My)
    "NA",   # 3.4 Material Genético (Mn)
    "SI",   # 3.5 Identificación Áreas (Mn)
    "NA",   # 4.1 Zona Espera (My)
    "NA",   # 4.2 Instalaciones Ordeño Fijo (F)
    "SI",   # 4.3 Instalaciones Ordeño Móvil (F)
    "SI",   # 4.4 Instalaciones Sanitarias (Mn)
    "SI",   # 4.5 Rutina Ordeño (F)
    "SI",   # 4.6 Equipos y Utensilios (F)
    "SI",   # 4.7 Disposición Leche Anormal (F)
    "SI",   # 4.8 Agua para Ordeño (My)
    "SI",   # 4.9 Conservación Leche (My)
    "NA",   # 5.1 Cuarto Tanque Leche (F)
    "NA",   # 5.2 Registro Temperatura (My)
    "SI",   # 6.1 Productos Registro ICA (F)
    "SI",   # 6.2 Productos No Vencidos (F)
    "SI",   # 6.3 Almacenamiento Medicamentos (My)
    "NA",   # 6.4 Sustancias Prohibidas (F)
    "NA",   # 6.5 Materias Primas Medicamento (F)
    "SI",   # 6.6 Tiempos de Retiro (F)
    "NO",   # 6.7 Prescripción Veterinaria (F)
    "SI",   # 6.8 Registros Tratamientos (F)
    "SI",   # 6.9 Equipos Administración (My)
    "SI",   # 6.10 Inventario Productos (My)
    "SI",   # 6.11 Autorización Aplicación (My)
    "SI",   # 6.12 Notificación Eventos Adversos (My)
    "SI",   # 7.1 Alimentos Registro ICA (F)
    "NA",   # 7.2 Alimento Medicado (F)
    "NO",   # 7.3 Prohibiciones Alimentarias (F)
    "NA",   # 7.4 Subproductos (My)
    "SI",   # 7.5 Insumos Agrícolas (F)
    "SI",   # 7.6 Inventario Alimentos (Mn)
    "NA",   # 7.7 Calidad Agua (My)
    "SI",   # 8.1 Limpieza Áreas (My)
    "SI",   # 8.2 Ubicación Predio (My)
    "SI",   # 8.3 Protección Fuentes Hídricas (My)
    "SI",   # 8.4 Disposición Estiércol (My)
    "SI",   # 8.5 Manejo Residuos (My)
    "SI",   # 8.6 Almacenamiento Insumos (My)
    "SI",   # 8.7 Control Plagas (My)
    "SI",   # 9.1 Adaptación Animales (My)
    "SI",   # 9.2 Superficies y Espacio (My)
    "SI",   # 9.3 Agrupamiento Social (My)
    "NA",   # 9.4 Estabulación (My)
    "SI",   # 9.5 Enfermedades y Parásitos (My)
    "SI",   # 9.6 Alimentos y Agua (My)
    "SI",   # 9.7 Sacrificio Humanitario (My)
    "SI",   # 9.8 Manejo del Dolor (F)
    "SI",   # 9.9 Relación Hombre-Animal (My)
    "SI",   # 10.1 Capacitación Personal (F)
    "SI",   # 10.2 Uso de Implementos (Mn)
]

# Write criteria responses starting at column Q (col 17, 0-indexed = 16)
# Q = col 17 in 1-indexed Sheets notation
start_col_letter = 'Q'
end_col_letter = chr(ord('Q') + len(respuestas) - 1)

range_str = f"{start_col_letter}3:{end_col_letter}3"
print(f"Writing to range: {range_str}")
print(f"Number of responses: {len(respuestas)}")

# First write raw responses
body = {
    "valueInputOption": "RAW",
    "data": [{"range": range_str, "values": [respuestas]}]
}
response = service.spreadsheets().values().batchUpdate(
    spreadsheetId=SHEET_ID, body=body
).execute()
print("✅ Respuestas escritas en hoja")

# Now calculate results
# Tipos de criterio en orden
tipos = [
    "F","My","F","F","F","F","F",  # 1.1-1.7
    "F","My",                       # 2.1-2.2
    "My","My","My","Mn","Mn",      # 3.1-3.5
    "My","F","F","Mn","F","F","F","My","My",  # 4.1-4.9
    "F","My",                       # 5.1-5.2
    "F","F","My","F","F","F","F","F","F","My","My","My","My",  # 6.1-6.12
    "F","F","F","My","F","Mn","My", # 7.1-7.7
    "My","My","My","My","My","My","My",  # 8.1-8.7
    "My","My","My","My","My","My","My","F","My",  # 9.1-9.9
    "F","Mn"                        # 10.1-10.2
]

# Count
f_total = tipos.count("F")
my_total = tipos.count("My")
mn_total = tipos.count("Mn")

# Count cumplidos (SI) by type
f_cumpl = 0
my_cumpl = 0
mn_cumpl = 0

for r, t in zip(respuestas, tipos):
    if r == "SI":
        if t == "F":
            f_cumpl += 1
        elif t == "My":
            my_cumpl += 1
        elif t == "Mn":
            mn_cumpl += 1

f_pct = round((f_cumpl / f_total) * 100, 1)
my_pct = round((my_cumpl / my_total) * 100, 1)
mn_pct = round((mn_cumpl / mn_total) * 100, 1)

print(f"\n=== RESULTADOS SAN JOSÉ 5 ===")
print(f"Fundamentales: {f_cumpl}/{f_total} = {f_pct}%")
print(f"Mayores: {my_cumpl}/{my_total} = {my_pct}%")
print(f"Menores: {mn_cumpl}/{mn_total} = {mn_pct}%")

# Concepto según umbrales
concepto = ""
if f_pct >= 90 and my_pct >= 80 and mn_pct >= 70:
    concepto = "Certificable"
else:
    concepto = "Aplazado"

print(f"Concepto: {concepto}")

observacion = ""
recomendacion = ""

if concepto == "Certificable":
    observacion = "El predio cumple con los umbrales mínimos establecidos en la Resolución 067449 para obtener la certificación en Buenas Prácticas Ganaderas."
    recomendacion = "Mantener y mejorar continuamente los registros documentales, especialmente en los criterios con respuesta NO."
else:
    observacion = f"El predio NO cumple con los umbrales mínimos. Fundamentales: {f_pct}% (requiere ≥90%), Mayores: {my_pct}% (requiere ≥80%), Menores: {mn_pct}% (requiere ≥70%)."
    recomendacion = "Se recomienda revisar los criterios con respuesta NO y NA que apliquen, priorizando los Fundamentales: Certificación de hatos libres (Art. 5.1.2), Prescripción veterinaria (Art. 8.9,8.15) y Prohibiciones alimentarias (Art. 9.6,9.7)."

# Write results to row 3 (columns for results start at index 78 in 0-based)
result_values = [f_cumpl, f_total, f_pct, my_cumpl, my_total, my_pct, mn_cumpl, mn_total, mn_pct, concepto, observacion, recomendacion]
result_start_col = 78 + 1  # 1-indexed for sheets
result_end_col = result_start_col + len(result_values) - 1

col_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# Column 79 = column CA (78+1=79 -> 26*2 + 27 = actually need proper calculation)
# Let's use column numbers directly
result_data = [result_values]
body = {
    "valueInputOption": "RAW",
    "data": [{"range": "CA3:CL3", "values": result_data}]
}
response = service.spreadsheets().values().batchUpdate(
    spreadsheetId=SHEET_ID, body=body
).execute()
print("✅ Resultados escritos en hoja")

# Verify
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='CA3:CL3'
).execute()
vals = result.get('values', [[]])[0]
print(f"\nResultados finales en hoja: {vals}")
