#!/usr/bin/env python3
"""
Script final para guardar auditoría usando OAuth manual
"""

import json
import os
import sys
from datetime import datetime

# Configuración
CREDENTIALS_FILE = "/home/ubuntu/.openclaw/workspace/credentials.json"
TOKEN_FILE = "/home/ubuntu/.openclaw/workspace/token.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = "1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg"

# Código de autorización proporcionado
AUTHORIZATION_CODE = "4/0Aci98E8ec9tR-5x7k4qC_R2rKV3RcuMjY0PxM1iQxORaZszRVmW_E41t9uMPSlEUMwFpSA"

def obtener_credenciales_desde_codigo():
    """Obtener credenciales desde el código de autorización"""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        import google.auth
        
        print("🔐 PROCESANDO CÓDIGO DE AUTORIZACIÓN...")
        
        # Configurar para desarrollo (permite HTTP localhost)
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
        # Cargar configuración del cliente
        with open(CREDENTIALS_FILE, 'r') as f:
            client_config = json.load(f)['installed']
        
        # Parámetros para intercambiar código por token
        token_url = 'https://oauth2.googleapis.com/token'
        
        import requests
        
        # Preparar datos para la solicitud
        token_data = {
            'code': AUTHORIZATION_CODE,
            'client_id': client_config['client_id'],
            'client_secret': client_config['client_secret'],
            'redirect_uri': 'http://localhost',
            'grant_type': 'authorization_code'
        }
        
        # Solicitar token
        response = requests.post(token_url, data=token_data)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo token: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return None
        
        token_info = response.json()
        
        # Crear credenciales
        creds = Credentials(
            token=token_info['access_token'],
            refresh_token=token_info.get('refresh_token'),
            token_uri=client_config['token_uri'],
            client_id=client_config['client_id'],
            client_secret=client_config['client_secret'],
            scopes=SCOPES
        )
        
        # Guardar token para uso futuro
        token_data_save = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data_save, f)
        
        print("✅ Credenciales obtenidas y guardadas")
        return creds
        
    except Exception as e:
        print(f"❌ Error obteniendo credenciales: {e}")
        import traceback
        traceback.print_exc()
        return None

def guardar_en_google_sheets():
    """Guardar auditoría en Google Sheets"""
    try:
        import gspread
        
        print("\n📊 CONECTANDO CON GOOGLE SHEETS...")
        
        # Obtener credenciales
        creds = obtener_credenciales_desde_codigo()
        if not creds:
            return False
        
        # Autenticar con gspread
        client = gspread.authorize(creds)
        
        # Abrir la hoja de cálculo
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            print(f"✅ Hoja encontrada: {spreadsheet.title}")
        except Exception as e:
            print(f"❌ Error abriendo la hoja: {e}")
            print("💡 Verifique que la hoja esté compartida con su cuenta")
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
        print("=" * 50)
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
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
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
    
    # Guardar en Google Sheets
    if guardar_en_google_sheets():
        print("\n✅ Proceso completado exitosamente")
        print("💡 El token se guardó para futuras conexiones automáticas")
    else:
        print("\n❌ No se pudo guardar en Google Sheets")

if __name__ == '__main__':
    main()