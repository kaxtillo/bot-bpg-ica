#!/usr/bin/env python3
"""
Enfoque simple para OAuth - Solo genera URL
"""

import json
import os

# Configuración
CREDENTIALS_FILE = "/home/ubuntu/.openclaw/workspace/credentials.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def generar_url_simple():
    """Generar URL simple de autorización"""
    try:
        # Cargar credenciales
        with open(CREDENTIALS_FILE, 'r') as f:
            client_config = json.load(f)['installed']
        
        client_id = client_config['client_id']
        redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'  # Para copiar/pegar código
        
        # Construir URL manualmente
        auth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope={'+'.join(SCOPES)}&"
            f"access_type=offline&"
            f"prompt=consent"
        )
        
        print("🔐 URL DE AUTORIZACIÓN SIMPLE")
        print("=" * 60)
        print("\n1. VISITE ESTA URL EN SU NAVEGADOR:")
        print(f"\n{auth_url}")
        print("\n2. SIGA ESTOS PASOS:")
        print("   a. Inicie sesión con su cuenta de Google")
        print("   b. Otorgue los permisos para Google Sheets")
        print("   c. Se mostrará un código de autorización")
        print("   d. Copie ese código")
        print("\n3. ENVÍEME EL CÓDIGO DE AUTORIZACIÓN")
        print("\n" + "=" * 60)
        
        return auth_url
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == '__main__':
    print("🔄 GENERANDO URL DE AUTORIZACIÓN")
    print("=" * 60)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ No se encontró: {CREDENTIALS_FILE}")
        exit(1)
    
    url = generar_url_simple()
    if url:
        print("\n✅ URL generada exitosamente")
    else:
        print("\n❌ Error generando URL")