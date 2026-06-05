#!/usr/bin/env python3
"""
Script para guardar auditorías BPG en Google Sheets usando OAuth 2.0
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuración
CREDENTIALS_FILE = "/home/ubuntu/.openclaw/workspace/credentials.json"
TOKEN_FILE = "/home/ubuntu/.openclaw/workspace/token.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

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
                print("1. Se abrirá una ventana del navegador para autenticarse")
                print("2. Inicie sesión con su cuenta de Google")
                print("3. Otorgue los permisos solicitados")
                print("4. Copie el código de autorización y péguelo aquí")
                print("\n💡 Si no se abre el navegador, visite la URL que se mostrará")
                print("-" * 50)
                
                # Ejecutar el flujo localmente (requiere interacción del usuario)
                creds = flow.run_local_server(port=0)
            
            # Guardar las credenciales para la próxima vez
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        return creds
        
    except ImportError:
        print("❌ Bibliotecas de Google no instaladas")
        print("💡 Ejecuta: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return None
    except Exception as e:
        print(f"❌ Error en autenticación OAuth: {e}")
        return None

def guardar_en_google_sheets_oauth(datos, spreadsheet_id):
    """Guardar auditoría en Google Sheets usando OAuth 2.0"""
    try:
        import gspread
        
        # Obtener credenciales OAuth
        creds = obtener_token_oauth()
        if not creds:
            return False
        
        # Autenticar con gspread
        client = gspread.authorize(creds)
        
        # Abrir la hoja de cálculo
        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
        except Exception as e:
            print(f"❌ Error abriendo la hoja de cálculo: {e}")
            print("💡 Verifique:")
            print("   1. El ID de la hoja es correcto")
            print("   2. La hoja está compartida con su cuenta de Google")
            print("   3. Tiene permisos de edición")
            return False
        
        # Seleccionar la primera hoja
        worksheet = spreadsheet.sheet1
        
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
        worksheet.append_row(fila)
        
        print(f"✅ Auditoría guardada en Google Sheets")
        print(f"   📊 Hoja: {spreadsheet.title}")
        print(f"   📍 URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error guardando en Google Sheets: {e}")
        return False

def guardar_auditoria_local(datos, filename=None):
    """Guardar auditoría en un archivo local"""
    try:
        # Crear directorio si no existe
        auditorias_dir = "/home/ubuntu/.openclaw/workspace/auditorias"
        os.makedirs(auditorias_dir, exist_ok=True)
        
        # Crear nombre de archivo con timestamp
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{auditorias_dir}/auditoria_{timestamp}.json"
        
        # Agregar timestamp a los datos
        datos_completos = {
            'timestamp': datetime.now().isoformat(),
            'auditoria': datos
        }
        
        # Guardar en archivo
        with open(filename, 'w') as f:
            json.dump(datos_completos, f, indent=2)
        
        print(f"📁 Auditoría guardada localmente: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error guardando localmente: {e}")
        return None

def main():
    """Función principal"""
    print("📊 GUARDAR AUDITORÍA BPG EN GOOGLE SHEETS")
    print("=" * 60)
    
    # Leer datos desde stdin o usar datos de prueba
    try:
        datos = json.loads(sys.stdin.read())
    except:
        # Cargar datos de la auditoría SAN JOSÉ 5
        try:
            with open('/home/ubuntu/.openclaw/workspace/auditoria_san_jose5.json', 'r') as f:
                datos = json.load(f)
        except:
            # Datos de prueba
            datos = {
                'predio': 'SAN JOSÉ 5',
                'propietario': 'Edison Lozada Mensa',
                'cedula': '1064676804',
                'municipio': 'Sotará',
                'vereda': 'Piedra de León',
                'telefono': '3105162252',
                'gps': '2.241723, -76.554590',
                'concepto': 'Certificable',
                'fundamentales_porcentaje': '100%',
                'mayores_porcentaje': '96.15%',
                'menores_porcentaje': '100%',
                'observaciones': '1.2: Requiere certificación hatos libres; 7.7: Requiere monitoreo agua',
                'resultados': {
                    'total_puntos': 62,
                    'puntos_si': 57,
                    'puntos_no': 2,
                    'puntos_na': 3
                }
            }
    
    # Mostrar resumen
    print(f"\n📋 RESUMEN DE AUDITORÍA:")
    print(f"  Predio: {datos.get('predio', 'No especificado')}")
    print(f"  Propietario: {datos.get('propietario', 'No especificado')}")
    print(f"  Concepto: {datos.get('concepto', 'No especificado')}")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Guardar localmente
    print("\n" + "=" * 60)
    archivo_local = guardar_auditoria_local(datos)
    
    if not archivo_local:
        print("❌ No se pudo guardar localmente")
        return
    
    # 2. Preguntar por el ID de la hoja de cálculo
    print("\n🌐 CONFIGURACIÓN GOOGLE SHEETS")
    print("-" * 60)
    
    # Verificar si hay credenciales
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ No se encontró el archivo de credenciales: {CREDENTIALS_FILE}")
        return
    
    print(f"✅ Credenciales encontradas: {CREDENTIALS_FILE}")
    
    # Solicitar ID de la hoja
    spreadsheet_id = input("\n📝 Ingrese el ID de su hoja de cálculo de Google Sheets: ").strip()
    
    if not spreadsheet_id:
        print("❌ No se proporcionó ID de hoja de cálculo")
        return
    
    # 3. Intentar guardar en Google Sheets
    print("\n" + "=" * 60)
    print("🔄 CONECTANDO CON GOOGLE SHEETS...")
    
    if guardar_en_google_sheets_oauth(datos, spreadsheet_id):
        print("\n🎉 ¡Auditoría guardada exitosamente en Google Sheets!")
    else:
        print("\n⚠️  No se pudo guardar en Google Sheets, pero se guardó localmente")

if __name__ == '__main__':
    main()