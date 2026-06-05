#!/usr/bin/env python3
"""
Script para autenticación manual OAuth 2.0
"""

import json
import os
from google_auth_oauthlib.flow import Flow

# Configuración
CREDENTIALS_FILE = "/home/ubuntu/.openclaw/workspace/credentials.json"
TOKEN_FILE = "/home/ubuntu/.openclaw/workspace/token.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def autenticar_manual():
    """Generar URL para autenticación manual"""
    try:
        # Cargar credenciales
        with open(CREDENTIALS_FILE, 'r') as f:
            client_config = json.load(f)
        
        # Crear flujo OAuth
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri='http://localhost'
        )
        
        # Generar URL de autorización
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        print("🔐 AUTENTICACIÓN MANUAL REQUERIDA")
        print("=" * 60)
        print("1. Visite esta URL en su navegador:")
        print(f"\n   {auth_url}")
        print("\n2. Inicie sesión con su cuenta de Google")
        print("3. Otorgue los permisos solicitados")
        print("4. Será redirigido a una página de error (esto es normal)")
        print("5. Copie la URL completa a la que fue redirigido")
        print("6. Péguela cuando se le solicite")
        print("\n" + "=" * 60)
        
        # Solicitar URL de redirección
        redirect_url = input("\n📋 Pegue la URL de redirección completa: ").strip()
        
        # Extraer código de autorización
        flow.fetch_token(authorization_response=redirect_url)
        
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
        
        print(f"\n✅ Autenticación exitosa!")
        print(f"✅ Token guardado en: {TOKEN_FILE}")
        
        return creds
        
    except Exception as e:
        print(f"❌ Error en autenticación: {e}")
        return None

def guardar_auditoria():
    """Guardar auditoría después de autenticar"""
    try:
        import gspread
        from datetime import datetime
        
        # Autenticar
        creds = autenticar_manual()
        if not creds:
            return False
        
        # Autenticar con gspread
        client = gspread.authorize(creds)
        
        # ID de la hoja
        SPREADSHEET_ID = "1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg"
        
        # Abrir la hoja de cálculo
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.sheet1
        
        # Cargar datos
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
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    print("📊 AUTENTICACIÓN MANUAL PARA GOOGLE SHEETS")
    print("=" * 60)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ No se encontró: {CREDENTIALS_FILE}")
        exit(1)
    
    if not os.path.exists('/home/ubuntu/.openclaw/workspace/auditoria_san_jose5.json'):
        print("❌ No se encontró el archivo de auditoría")
        exit(1)
    
    guardar_auditoria()