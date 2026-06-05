#!/usr/bin/env python3
"""
Enfoque directo para guardar auditoría
"""

import json
import os
import requests
from datetime import datetime

# Configuración
CREDENTIALS_FILE = "/home/ubuntu/.openclaw/workspace/credentials.json"
TOKEN_FILE = "/home/ubuntu/.openclaw/workspace/token_direct.json"
SPREADSHEET_ID = "1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg"

# Código de autorización
AUTHORIZATION_CODE = "4/0Aci98E9V_mDF2RL7mUotLXzen7WfLH0DmRtXaqTvpcDOf1Wkjj_QYvAS_3DjOHDA3NbH_A"

def obtener_token_directo():
    """Obtener token directamente con el código"""
    try:
        print("🔐 OBTENIENDO TOKEN DE ACCESO...")
        
        # Cargar configuración del cliente
        with open(CREDENTIALS_FILE, 'r') as f:
            client_config = json.load(f)['installed']
        
        # Parámetros para el intercambio de código
        token_url = 'https://oauth2.googleapis.com/token'
        
        token_data = {
            'code': AUTHORIZATION_CODE,
            'client_id': client_config['client_id'],
            'client_secret': client_config['client_secret'],
            'redirect_uri': 'http://localhost:8080',
            'grant_type': 'authorization_code'
        }
        
        # Solicitar token
        response = requests.post(token_url, data=token_data)
        
        print(f"📡 Respuesta del servidor: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
            return None
        
        token_info = response.json()
        
        print(f"✅ Token obtenido exitosamente")
        print(f"   • Access token: {token_info.get('access_token', '')[:20]}...")
        print(f"   • Refresh token: {'Sí' if 'refresh_token' in token_info else 'No'}")
        print(f"   • Expira en: {token_info.get('expires_in', '')} segundos")
        
        # Guardar token
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_info, f, indent=2)
        
        return token_info
        
    except Exception as e:
        print(f"❌ Error obteniendo token: {e}")
        return None

def guardar_en_sheets_con_token(token_info):
    """Guardar auditoría usando el token de acceso"""
    try:
        import gspread
        from google.oauth2.credentials import Credentials
        
        print("\n📊 CONECTANDO CON GOOGLE SHEETS...")
        
        # Crear credenciales desde el token
        creds = Credentials(
            token=token_info['access_token'],
            refresh_token=token_info.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=token_info.get('client_id', ''),
            client_secret=token_info.get('client_secret', ''),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Autenticar con gspread
        client = gspread.authorize(creds)
        
        # Abrir la hoja de cálculo
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            print(f"✅ Hoja encontrada: {spreadsheet.title}")
        except Exception as e:
            print(f"❌ Error abriendo la hoja: {e}")
            print("💡 Verifique que la hoja esté compartida con su cuenta de Google")
            return False
        
        # Seleccionar primera hoja
        worksheet = spreadsheet.sheet1
        
        # Cargar datos de la auditoría
        with open('/home/ubuntu/.openclaw/workspace/auditoria_san_jose5.json', 'r') as f:
            datos = json.load(f)
        
        # Verificar encabezados
        try:
            headers = worksheet.row_values(1)
        except:
            headers = []
        
        # Agregar encabezados si es necesario
        if not headers:
            headers = [
                'Fecha', 'Predio', 'Propietario', 'Cédula', 'Municipio', 'Vereda',
                'Teléfono', 'GPS', 'Concepto', 'Fundamentales %', 'Mayores %', 
                'Menores %', 'Observaciones', 'Total Puntos', 'Puntos SI', 
                'Puntos NO', 'Puntos NA'
            ]
            worksheet.append_row(headers)
            print("✅ Encabezados agregados")
        
        # Preparar fila
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
        
        # Insertar fila
        print("📝 Insertando datos...")
        worksheet.append_row(fila)
        
        print(f"\n🎉 ¡AUDITORÍA GUARDADA EXITOSAMENTE!")
        print("=" * 60)
        print(f"📊 Hoja: {spreadsheet.title}")
        print(f"📍 URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        print(f"📅 Fecha: {timestamp}")
        print(f"🏠 Predio: {datos.get('predio', '')}")
        print(f"👤 Propietario: {datos.get('propietario', '')}")
        print(f"📞 Teléfono: {datos.get('telefono', '')}")
        print(f"📍 GPS: {datos.get('gps', '')}")
        print(f"✅ Concepto: {datos.get('concepto', '')}")
        print(f"📊 Fundamentales: {datos.get('fundamentales_porcentaje', '')}")
        print(f"📊 Mayores: {datos.get('mayores_porcentaje', '')}")
        print(f"📊 Menores: {datos.get('menores_porcentaje', '')}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error guardando en Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    print("📊 GUARDAR AUDITORÍA SAN JOSÉ 5 EN GOOGLE SHEETS")
    print("=" * 60)
    
    # Verificar archivos
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ No se encontró: {CREDENTIALS_FILE}")
        return
    
    if not os.path.exists('/home/ubuntu/.openclaw/workspace/auditoria_san_jose5.json'):
        print("❌ No se encontró el archivo de auditoría")
        return
    
    # Obtener token
    token_info = obtener_token_directo()
    if not token_info:
        print("\n❌ No se pudo obtener el token")
        return
    
    # Guardar auditoría
    if guardar_en_sheets_con_token(token_info):
        print("\n✅ ¡PROCESO COMPLETADO EXITOSAMENTE!")
        print("💡 Puede verificar la auditoría en su Google Sheets")
        print("💡 El token se guardó para futuras conexiones")
    else:
        print("\n❌ No se pudo guardar en Google Sheets")

if __name__ == '__main__':
    main()