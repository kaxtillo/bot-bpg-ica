#!/usr/bin/env python3
"""
Completar autenticación OAuth y guardar auditoría
"""

import json
import os
from google_auth_oauthlib.flow import Flow
import gspread
from datetime import datetime

# Configuración
CREDENTIALS_FILE = "/home/ubuntu/.openclaw/workspace/credentials.json"
TOKEN_FILE = "/home/ubuntu/.openclaw/workspace/token.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = "1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg"

# URL de redirección proporcionada por el usuario
REDIRECT_URL = "http://localhost/?state=DojClvUA3Lzq6wtoZvLgnx3mwaGYh6&iss=https://accounts.google.com&code=4/0Aci98E8ec9tR-5x7k4qC_R2rKV3RcuMjY0PxM1iQxORaZszRVmW_E41t9uMPSlEUMwFpSA&scope=email%20https://www.googleapis.com/auth/spreadsheets%20https://www.googleapis.com/auth/drive%20openid%20https://www.googleapis.com/auth/userinfo.email&authuser=0&hd=estudiantes.areandina.edu.co&prompt=consent"

def completar_autenticacion():
    """Completar autenticación OAuth con la URL de redirección"""
    try:
        print("🔐 COMPLETANDO AUTENTICACIÓN...")
        
        # Cargar credenciales
        with open(CREDENTIALS_FILE, 'r') as f:
            client_config = json.load(f)
        
        # Crear flujo OAuth
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri='http://localhost'
        )
        
        # Usar la URL de redirección para obtener el token
        flow.fetch_token(authorization_response=REDIRECT_URL)
        
        # Obtener credenciales
        creds = flow.credentials
        
        # Guardar token
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f)
        
        print(f"✅ Autenticación exitosa!")
        print(f"✅ Token guardado en: {TOKEN_FILE}")
        
        return creds
        
    except Exception as e:
        print(f"❌ Error en autenticación: {e}")
        return None

def guardar_auditoria_en_sheets(creds):
    """Guardar auditoría en Google Sheets"""
    try:
        print("\n📊 CONECTANDO CON GOOGLE SHEETS...")
        
        # Autenticar con gspread
        client = gspread.authorize(creds)
        
        # Abrir la hoja de cálculo
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.sheet1
        
        print(f"✅ Hoja encontrada: {spreadsheet.title}")
        
        # Cargar datos de la auditoría
        with open('/home/ubuntu/.openclaw/workspace/auditoria_san_jose5.json', 'r') as f:
            datos = json.load(f)
        
        # Verificar si la hoja tiene encabezados
        try:
            headers = worksheet.row_values(1)
        except:
            headers = []
        
        # Si la hoja está vacía, agregar encabezados
        if not headers:
            headers = [
                'Fecha', 'Predio', 'Propietario', 'Cédula', 'Municipio', 'Vereda',
                'Teléfono', 'GPS', 'Concepto', 'Fundamentales %', 'Mayores %', 
                'Menores %', 'Observaciones', 'Total Puntos', 'Puntos SI', 
                'Puntos NO', 'Puntos NA'
            ]
            worksheet.append_row(headers)
            print("✅ Encabezados agregados a la hoja")
        
        # Preparar datos para insertar
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        resultados = datos.get('resultados', {})
        
        fila = [
            timestamp,
            datos.get('predio', ''),
            datos.get('propietario', ''),
            datos.get('cedula', ''),
            datos.get('municipio', ''),
            datos.get('vereda', ''),
            datos.get('telefono', ''),
            datos.get('gps', ''),
            datos.get('concepto', ''),
            datos.get('fundamentales_porcentaje', ''),
            datos.get('mayores_porcentaje', ''),
            datos.get('menores_porcentaje', ''),
            datos.get('observaciones', ''),
            str(resultados.get('total_puntos', '')),
            str(resultados.get('puntos_si', '')),
            str(resultados.get('puntos_no', '')),
            str(resultados.get('puntos_na', ''))
        ]
        
        # Insertar nueva fila
        print("📝 Insertando datos en la hoja...")
        worksheet.append_row(fila)
        
        print(f"\n🎉 ¡AUDITORÍA GUARDADA EXITOSAMENTE!")
        print("=" * 50)
        print(f"📊 Hoja: {spreadsheet.title}")
        print(f"📍 URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        print(f"📅 Fecha: {timestamp}")
        print(f"🏠 Predio: {datos.get('predio', '')}")
        print(f"👤 Propietario: {datos.get('propietario', '')}")
        print(f"✅ Concepto: {datos.get('concepto', '')}")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ Error guardando en Google Sheets: {e}")
        return False

def main():
    """Función principal"""
    print("📊 GUARDAR AUDITORÍA SAN JOSÉ 5 EN GOOGLE SHEETS")
    print("=" * 60)
    
    # Verificar archivos necesarios
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ No se encontró: {CREDENTIALS_FILE}")
        return
    
    if not os.path.exists('/home/ubuntu/.openclaw/workspace/auditoria_san_jose5.json'):
        print("❌ No se encontró el archivo de auditoría")
        return
    
    # Completar autenticación
    creds = completar_autenticacion()
    if not creds:
        return
    
    # Guardar auditoría
    if guardar_auditoria_en_sheets(creds):
        print("\n✅ Proceso completado exitosamente")
        print("💡 El token se guardó para futuras conexiones")
    else:
        print("\n❌ No se pudo guardar en Google Sheets")

if __name__ == '__main__':
    main()