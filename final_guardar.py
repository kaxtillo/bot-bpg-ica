#!/usr/bin/env python3
"""
Guardar auditoría con el nuevo código de autorización
"""

import json
import os
import requests
from datetime import datetime

# Configuración
CREDENTIALS_FILE = "/home/ubuntu/.openclaw/workspace/credentials.json"
TOKEN_FILE = "/home/ubuntu/.openclaw/workspace/token_final.json"
SPREADSHEET_ID = "1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg"

# Nuevo código de autorización
AUTHORIZATION_CODE = "4/1Aci98E_suHnj-u94X5oBJIzPjttMPnj4bEjlxdG91XGnzhkJ-adrKmiMRbM"

def intercambiar_codigo_por_token():
    """Intercambiar código de autorización por token de acceso"""
    try:
        print("🔄 INTERCAMBIANDO CÓDIGO POR TOKEN...")
        
        # Cargar configuración del cliente
        with open(CREDENTIALS_FILE, 'r') as f:
            client_config = json.load(f)['installed']
        
        # Parámetros para la solicitud
        token_url = 'https://oauth2.googleapis.com/token'
        
        token_data = {
            'code': AUTHORIZATION_CODE,
            'client_id': client_config['client_id'],
            'client_secret': client_config['client_secret'],
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'authorization_code'
        }
        
        # Enviar solicitud
        response = requests.post(token_url, data=token_data)
        
        print(f"📡 Estado de respuesta: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Error en la respuesta: {response.text}")
            return None
        
        token_info = response.json()
        
        print("✅ Token obtenido exitosamente!")
        print(f"   • Access token: {token_info.get('access_token', '')[:30]}...")
        print(f"   • Tiene refresh token: {'Sí' if 'refresh_token' in token_info else 'No'}")
        
        # Guardar token
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_info, f, indent=2)
        
        print(f"💾 Token guardado en: {TOKEN_FILE}")
        
        return token_info
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def guardar_auditoria_en_google_sheets(token_info):
    """Guardar la auditoría en Google Sheets"""
    try:
        import gspread
        from google.oauth2.credentials import Credentials
        
        print("\n📊 CONECTANDO CON GOOGLE SHEETS...")
        
        # Crear credenciales
        creds = Credentials(
            token=token_info['access_token'],
            refresh_token=token_info.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=token_info.get('client_id', ''),
            client_secret=token_info.get('client_secret', ''),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Autenticar
        client = gspread.authorize(creds)
        
        # Abrir hoja de cálculo
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            print(f"✅ Hoja encontrada: {spreadsheet.title}")
        except Exception as e:
            print(f"❌ Error abriendo la hoja: {e}")
            print("💡 Asegúrese de que la hoja esté compartida con su cuenta")
            return False
        
        worksheet = spreadsheet.sheet1
        
        # Cargar datos de auditoría
        with open('/home/ubuntu/.openclaw/workspace/auditoria_san_jose5.json', 'r') as f:
            datos = json.load(f)
        
        # Verificar/crear encabezados
        try:
            headers = worksheet.row_values(1)
        except:
            headers = []
        
        if not headers:
            headers = [
                'Fecha', 'Predio', 'Propietario', 'Cédula', 'Municipio', 'Vereda',
                'Teléfono', 'GPS', 'Concepto', 'Fundamentales %', 'Mayores %', 
                'Menores %', 'Observaciones', 'Total Puntos', 'Puntos SI', 
                'Puntos NO', 'Puntos NA'
            ]
            worksheet.append_row(headers)
            print("✅ Encabezados agregados")
        
        # Preparar datos
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
        print("📝 Insertando datos en la hoja...")
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
    archivos_requeridos = [
        (CREDENTIALS_FILE, "credenciales"),
        ('/home/ubuntu/.openclaw/workspace/auditoria_san_jose5.json', "datos de auditoría")
    ]
    
    for archivo, nombre in archivos_requeridos:
        if not os.path.exists(archivo):
            print(f"❌ No se encontró {nombre}: {archivo}")
            return
    
    print("✅ Todos los archivos requeridos encontrados")
    
    # Obtener token
    token_info = intercambiar_codigo_por_token()
    if not token_info:
        print("\n❌ No se pudo obtener el token de acceso")
        return
    
    # Guardar auditoría
    if guardar_auditoria_en_google_sheets(token_info):
        print("\n✅ ¡PROCESO COMPLETADO EXITOSAMENTE!")
        print("💡 La auditoría se guardó en su Google Sheets")
        print("💡 El token se guardó para futuras conexiones")
        print("\n📋 RESUMEN FINAL:")
        print("   • Auditoría: SAN JOSÉ 5")
        print("   • Propietario: Edison Lozada Mensa")
        print("   • Concepto: Certificable")
        print("   • Guardado en: Su Google Sheets")
    else:
        print("\n❌ No se pudo guardar en Google Sheets")

if __name__ == '__main__':
    main()