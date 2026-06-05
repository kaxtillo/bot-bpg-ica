#!/usr/bin/env python3
"""
Script SIMPLE para guardar auditorías BPG - Versión sin autenticación interactiva
"""

import json
import sys
from datetime import datetime

def guardar_auditoria_local(datos):
    """Guardar auditoría en un archivo local (como respaldo)"""
    try:
        # Crear nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"/home/ubuntu/.openclaw/workspace/auditorias/auditoria_{timestamp}.json"
        
        # Asegurar que el directorio existe
        import os
        os.makedirs("/home/ubuntu/.openclaw/workspace/auditorias", exist_ok=True)
        
        # Agregar timestamp a los datos
        datos_completos = {
            'timestamp': datetime.now().isoformat(),
            'auditoria': datos
        }
        
        # Guardar en archivo
        with open(filename, 'w') as f:
            json.dump(datos_completos, f, indent=2)
        
        print(f"📁 Auditoría guardada localmente: {filename}")
        
        # También mostrar resumen en consola
        print("\n📋 RESUMEN DE AUDITORÍA:")
        print(f"  Propietario: {datos.get('propietario', 'No especificado')}")
        print(f"  Predio: {datos.get('predio', 'No especificado')}")
        print(f"  Concepto: {datos.get('concepto', 'No especificado')}")
        print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
    except Exception as e:
        print(f"❌ Error guardando localmente: {e}")
        return False

if __name__ == '__main__':
    # Leer datos desde stdin o usar datos de prueba
    try:
        datos = json.loads(sys.stdin.read())
    except:
        # Datos de prueba
        datos = {
            'propietario': 'María Gómez',
            'predio': 'Finca La Pradera',
            'concepto': 'Certificable',
            'notas': 'Auditoría de prueba ejecutada desde OpenClaw'
        }
    
    if guardar_auditoria_local(datos):
        print("\n✅ Auditoría guardada exitosamente (modo local)")
        print("💡 Para guardar en Google Sheets, necesitas completar la autenticación OAuth manualmente")
    else:
        print("❌ Error guardando auditoría")
        sys.exit(1)