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

# Get row 3
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='A3:CL3'
).execute()
vals = result.get('values', [[]])[0]

print(f"Total valores fila 3: {len(vals)}")

# Columnas base (16)
base_cols = ["Fecha","Propietario","Identificación","Teléfono","Email",
    "Predio","Departamento","Municipio","Vereda","Latitud","Longitud",
    "RSPP","Especie","FinZootécnico","Producción","TotalAnimales"]
print("\n=== DATOS BASE ===")
for i, col in enumerate(base_cols):
    if i < len(vals):
        print(f"  {col}: {vals[i]}")

# Criterios (62) starting at index 16
crit_names = [
    "1.1 Plan Sanitario(F)","1.2 Cert Hatos(My)","1.3 Proto Aislam(F)","1.4 Reg Diag(F)","1.5 Inst Enf(F)","1.6 Enfermería(F)","1.7 Mastitis(F)",
    "2.1 Identif(F)","2.2 Reg Indiv(My)",
    "3.1 Delimit(My)","3.2 Reg Visit(My)","3.3 Cuarentena(My)","3.4 Mat Gen(Mn)","3.5 Id Áreas(Mn)",
    "4.1 Zona Espera(My)","4.2 Ord Fijo(F)","4.3 Ord Móvil(F)","4.4 SS HH(Mn)","4.5 Rutina Ord(F)","4.6 Equipos Ord(F)","4.7 Leche Anorm(F)","4.8 Agua Ord(My)","4.9 Conserv Leche(My)",
    "5.1 Tanque(F)","5.2 Reg Temp(My)",
    "6.1 Prod ICA(F)","6.2 No Venc(F)","6.3 Almac Med(My)","6.4 Sust Proh(F)","6.5 Mat Primas(F)","6.6 Tiempos Ret(F)","6.7 Prescripción(F)","6.8 Reg Trat(F)","6.9 Equipos Adm(My)","6.10 Invent(My)","6.11 Autoriz(My)","6.12 Event Adv(My)",
    "7.1 Alim ICA(F)","7.2 Alim Medic(F)","7.3 Prohib Alim(F)","7.4 Subprod(My)","7.5 Insumos Agr(F)","7.6 Invent Alim(Mn)","7.7 Calidad Agua(My)",
    "8.1 Limpieza(My)","8.2 Ubicación(My)","8.3 Fuentes Híd(My)","8.4 Estiércol(My)","8.5 Residuos(My)","8.6 Almac Insum(My)","8.7 Control Plag(My)",
    "9.1 Adaptación(My)","9.2 Superficies(My)","9.3 Agrup Social(My)","9.4 Estabulación(My)","9.5 Enf Parás(My)","9.6 Alim Agua(My)","9.7 Sacrif Hum(My)","9.8 Dolor(F)","9.9 Relac Hombre(My)",
    "10.1 Capacitac(F)","10.2 Implement(Mn)"
]

print("\n=== CRITERIOS CON NO ===")
for i, name in enumerate(crit_names):
    idx = 16 + i
    if idx < len(vals):
        val = vals[idx]
        if val == "NO":
            print(f"  {name}: {val} ❌")
        elif val == "SI":
            pass  # skip SI
        else:
            print(f"  {name}: {val}")

# Resultados starting at index 78
result_names = ["FCumplidos","FTotal","FPorcentaje","MyCumplidos","MyTotal","MyPorcentaje",
                "MnCumplidos","MnTotal","MnPorcentaje","Concepto","Observación","Recomendación"]
print("\n=== RESULTADOS ===")
for i, name in enumerate(result_names):
    idx = 78 + i
    if idx < len(vals):
        print(f"  {name}: {vals[idx]}")
