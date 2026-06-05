#!/usr/bin/env python3
"""
Script para guardar auditorías BPG en Google Sheets
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

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

def guardar_en_google_sheets(datos):
    """Guardar auditoría en Google Sheets"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Verificar si existe el archivo de credenciales
        creds_path = "/home/ubuntu/.openclaw/workspace/credentials.json"
        if not os.path.exists(creds_path):
            print("❌ No se encontró el archivo credentials.json")
            print("💡 Necesitas crear un archivo credentials.json con las credenciales de Google API")
            return False
        
        # Configurar alcances
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Autenticar
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # ID de la hoja de cálculo (debe ser proporcionado)
        # Ejemplo: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
        SPREADSHEET_ID = os.environ.get('GOOGLE_SHEET_ID', 'TU_SPREADSHEET_ID_AQUI')
        
        if SPREADSHEET_ID == 'TU_SPREADSHEET_ID_AQUI':
            print("❌ No se configuró el ID de la hoja de cálculo")
            print("💡 Configura la variable de entorno GOOGLE_SHEET_ID o edita el script")
            return False
        
        # Abrir la hoja de cálculo
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # Seleccionar la primera hoja (o una específica)
        worksheet = spreadsheet.sheet1
        
        # Preparar datos para insertar
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
            json.dumps(datos.get('resultados', {}))
        ]
        
        # Insertar nueva fila
        worksheet.append_row(fila)
        
        print(f"✅ Auditoría guardada en Google Sheets: {spreadsheet.title}")
        return True
        
    except ImportError:
        print("❌ Bibliotecas de Google no instaladas")
        print("💡 Ejecuta: pip install gspread google-auth")
        return False
    except Exception as e:
        print(f"❌ Error guardando en Google Sheets: {e}")
        return False

def main():
    """Función principal"""
    # Leer datos desde stdin o usar datos de prueba
    try:
        datos = json.loads(sys.stdin.read())
    except:
        # Datos de prueba basados en la auditoría SAN JOSÉ 5
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
    
    print("📊 PROCESANDO AUDITORÍA BPG")
    print("=" * 50)
    
    # 1. Guardar localmente
    archivo_local = guardar_auditoria_local(datos)
    
    if archivo_local:
        print(f"\n📋 RESUMEN DE AUDITORÍA:")
        print(f"  Predio: {datos.get('predio', 'No especificado')}")
        print(f"  Propietario: {datos.get('propietario', 'No especificado')}")
        print(f"  Cédula: {datos.get('cedula', 'No especificado')}")
        print(f"  Municipio: {datos.get('municipio', 'No especificado')}")
        print(f"  Concepto: {datos.get('concepto', 'No especificado')}")
        print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 2. Intentar guardar en Google Sheets
    print("\n🌐 INTENTANDO GUARDAR EN GOOGLE SHEETS...")
    print("-" * 50)
    
    # Verificar si hay credenciales
    creds_path = "/home/ubuntu/.openclaw/workspace/credentials.json"
    if os.path.exists(creds_path):
        print(f"✅ Credenciales encontradas: {creds_path}")
        if guardar_en_google_sheets(datos):
            print("\n🎉 ¡Auditoría guardada exitosamente en Google Sheets!")
        else:
            print("\n⚠️  No se pudo guardar en Google Sheets, pero se guardó localmente")
    else:
        print(f"❌ No se encontraron credenciales en: {creds_path}")
        print("\n📝 INSTRUCCIONES PARA CONFIGURAR GOOGLE SHEETS:")
        print("1. Crea un proyecto en Google Cloud Console")
        print("2. Habilita Google Sheets API")
        print("3. Crea una cuenta de servicio y descarga credentials.json")
        print("4. Coloca el archivo en: /home/ubuntu/.openclaw/workspace/credentials.json")
        print("5. Comparte tu hoja de cálculo con el email de la cuenta de servicio")
        print("6. Configura la variable de entorno GOOGLE_SHEET_ID con el ID de tu hoja")
        print("\n💡 Por ahora, la auditoría solo se guardó localmente")

if __name__ == '__main__':
    main()