#!/usr/bin/env python3
"""
Script específico para guardar la auditoría SAN JOSÉ 5 en Google Sheets
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

def obtener_token_oauth():
    """Obtener token de acceso OAuth 2.0"""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import google.oauth2.credentials
        
        creds = None
        
        # El archivo token.json almacena los tokens de acceso y actualización
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as token:
                creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
                    json.load(token), SCOPES)
        
        # Si no hay credenciales válidas, solicitar al usuario que se autentique
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    print(f"❌ No se encontró el archivo de credenciales: {CREDENTIALS_FILE}")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                print("\n🔐 AUTENTICACIÓN REQUERIDA")
                print("=" * 50)
                print("Se abrirá una ventana del navegador para autenticarse")
                print("Por favor, siga las instrucciones en pantalla")
                print("-" * 50)
                
                # Ejecutar el flujo localmente
                creds = flow.run_local_server(port=0)
            
            # Guardar las credenciales para la próxima vez
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        return creds
        
    except Exception as e:
        print(f"❌ Error en autenticación OAuth: {e}")
        return None

def guardar_en_google_sheets():
    """Guardar auditoría en Google Sheets"""
    try:
        import gspread
        
        # Obtener credenciales OAuth
        print("🔄 Obteniendo token de acceso...")
        creds = obtener_token_oauth()
        if not creds:
            return False
        
        # Autenticar con gspread
        print("🔗 Conectando con Google Sheets...")
        client = gspread.authorize(creds)
        
        # Abrir la hoja de cálculo
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            print(f"✅ Hoja encontrada: {spreadsheet.title}")
        except Exception as e:
            print(f"❌ Error abriendo la hoja de cálculo: {e}")
            print("💡 Verifique:")
            print("   1. El ID de la hoja es correcto")
            print("   2. La hoja está compartida con su cuenta de Google")
            print("   3. Tiene permisos de edición")
            return False
        
        # Seleccionar la primera hoja
        worksheet = spreadsheet.sheet1
        
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
    
    # Verificar archivo de datos
    if not os.path.exists('/home/ubuntu/.openclaw/workspace/auditoria_san_jose5.json'):
        print("❌ No se encontró el archivo de datos de la auditoría")
        return
    
    # Verificar credenciales
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ No se encontró el archivo de credenciales: {CREDENTIALS_FILE}")
        return
    
    print(f"✅ Credenciales encontradas: {CREDENTIALS_FILE}")
    print(f"✅ ID de hoja: {SPREADSHEET_ID}")
    
    # Guardar en Google Sheets
    print("\n" + "=" * 60)
    if guardar_en_google_sheets():
        print("\n✅ Proceso completado exitosamente")
    else:
        print("\n❌ No se pudo guardar en Google Sheets")

if __name__ == '__main__':
    main()