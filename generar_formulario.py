#!/usr/bin/env python3
"""
Genera el formulario de captura de auditoría BPG ICA en CSV (abre en
Excel/LibreOffice; también se puede imprimir para llenar a mano en la finca).

  python3 generar_formulario.py [salida.csv]

El formulario tiene una fila por criterio (columna Respuesta = SI/NO/NA) más
una sección de datos del predio. Llenado → procesar con:
  python3 auditar.py --archivo formulario.csv
"""
import csv
import os
import sqlite3
import sys

DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")
SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/auditorias_bpg/formulario_auditoria.csv"
)


def main():
    con = sqlite3.connect(DB)
    crit = con.execute(
        """SELECT id, nombre, tipo, articulo, pregunta FROM criterios
           ORDER BY CAST(substr(id,1,instr(id,'.')-1) AS INT), CAST(substr(id,instr(id,'.')+1) AS INT)"""
    ).fetchall()
    con.close()

    with open(SALIDA, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SECCIÓN", "CAMPO", "VALOR", "NOTAS"])
        w.writerow(["predio", "predio_predio", "", "Nombre del predio (obligatorio)"])
        w.writerow(["predio", "predio_propietario", "", "Nombre del propietario (obligatorio)"])
        w.writerow(["predio", "predio_identificacion", "", "Cédula"])
        w.writerow(["predio", "predio_municipio", "", "Municipio (obligatorio)"])
        w.writerow(["predio", "predio_vereda", "", "Vereda"])
        w.writerow(["predio", "predio_telefono", "", "Teléfono"])
        w.writerow(["predio", "predio_gps", "", "Lat, lon (ej. 2.597141, -76.614733)"])
        w.writerow([])
        w.writerow(["N°", "CRITERIO", "TIPO", "ART.", "PREGUNTA", "RESPUESTA (SI/NO/NA)", "NOTAS"])
        for cid, nombre, tipo, art, pregunta in crit:
            w.writerow([cid, nombre, tipo, art, pregunta, "", ""])

    print(f"✅ Formulario generado: {SALIDA}")
    print(f"   ({len(crit)} criterios + datos del predio)")
    print("   Llénelo (Excel/LibreOffice o impreso) y procese con:")
    print("   python3 ~/auditorias_bpg/auditar.py --archivo formulario_auditoria.csv")


if __name__ == "__main__":
    main()
