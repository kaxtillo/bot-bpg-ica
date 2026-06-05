#!/usr/bin/env python3
"""
Procesar código de autorización y guardar auditoría
"""

import json
import os
from datetime import datetime

# Configuración
CREDENTIALS_FILE = "/home/ubuntu/.openclaw/workspace/credentials.json"
TOKEN_FILE = "/home/ubuntu/.openclaw/workspace/token.json"
STATE_FILE = "/home/ubuntu/.openclaw/workspace/oauth_state.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = "1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg"

# URL de redirección
REDIRECT_URL = "http://localhost:8080/?state=lEC6FXZUF3krOrMnM2QAaKZmoC4uTA&iss=https://accounts.google.com&code=4/0Aci98E9V_mDF2RL7mUotLXzen7WfLH0DmRtXaqTvpcDOf1Wkjj_QYvAS_3DjOHDA3NbH_A&scope=email%20https://www.googleapis.com/auth/spreadsheets%20https://www.googleapis.com/auth/drive%20openid%20https://www.googleapis.com/auth/userinfo.email&authuser=0&hd=estudiantes.areandina.edu.co&prompt=consent"

def procesar_autorizacion():
    """Procesar la autorización OAuth"""
    try:
        # Configurar para desarrollo
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
        from google_auth_oauthlib.flow import Flow
        
        print("🔐 PROCESANDO AUTORIZACIÓN...")
        
        # Cargar estado guardado
        if not os.path.exists(STATE_FILE):
            print("❌ No se encontró el archivo de estado")
            return None
        
        with open(STATE_FILE, 'r') as f:
            state_data = json.load(f)
        
        # Recrear el flujo (simplificado)
        with open(CREDENTIALS_FILE, 'r') as f:
            client_config = json.load(f)
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri='http://localhost:8080'
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
        
        print("✅ Autenticación exitosa!")
        print(f"✅ Token guardado en: {TOKEN_FILE}")
        
        return creds
        
    except Exception as e:
        print(f"❌ Error en autenticación: {e}")
        import traceback
        traceback.print_exc()
        return None

def guardar_auditoria(creds):
    """Guardar auditoría en Google Sheets"""
    try:
        import gspread
        
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
        
        # Mostrar detalles adicionales
        print("\n📋 DETALLES DE LA AUDITORÍA:")
        print(f"  • Total puntos evaluados: {resultados.get('total_puntos', '')}")
        print(f"  • Puntos cumplidos (SI): {resultados.get('puntos_si', '')}")
        print(f"  • Puntos no cumplidos (NO): {resultados.get('puntos_no', '')}")
        print(f"  • Puntos no aplica (NA): {resultados.get('puntos_na', '')}")
        print(f"  • Observaciones: {datos.get('observaciones', '')}")
        
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
    
    # Procesar autorización
    creds = procesar_autorizacion()
    if not creds:
        print("\n❌ No se pudo autenticar")
        return
    
    # Guardar auditoría
    if guardar_auditoria(creds):
        print("\n✅ ¡PROCESO COMPLETADO EXITOSAMENTE!")
        print("💡 El token se guardó para futuras conexiones automáticas")
        print("💡 Puede verificar la auditoría en su Google Sheets")
    else:
        print("\n❌ No se pudo guardar en Google Sheets")

if __name__ == '__main__':
    main()