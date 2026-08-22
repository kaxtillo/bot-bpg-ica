#!/usr/bin/env python3
"""
Sincronización bidireccional entre la hoja de Google Sheets
("Auditorias BPG ICA - Produccion de Leche") y la base local.

1. Descarga la hoja a CSV (export) y consolida en la BD local
   (importar_hoja.py — idempotente, sin duplicados).
2. Detecta auditorías de la BD local que NO tienen fila en la hoja
   y las escribe con append (formato real de la hoja: 89 columnas,
   cabecera C1.1|F, sin columna Fecha).

Uso: python3 sincronizar_hoja.py [--push] [--pull]
  --push : escribir en la hoja las auditorías locales faltantes (por defecto)
  --pull : solo leer la hoja e importar a la BD
"""
import csv
import json
import os
import sqlite3
import subprocess
import sys
from datetime import date

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
GAPI = ["python", os.path.join(HERMES_HOME, "skills/productivity/google-workspace/scripts/google_api.py")]
SHEET = "1_HLqkdv5EBvQzRF5iMfpAw6fUI96aTj9ROxkwPan4Eg"
TAB = "Hoja 1"
DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")
IMPORTADOR = os.path.expanduser("~/auditorias_bpg/importar_hoja.py")
CSV_TMP = "/tmp/hoja_sync.csv"


def descargar_hoja():
    r = subprocess.run(GAPI + ["drive", "download", SHEET, "--export-mime", "text/csv", "--output", CSV_TMP],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("❌ Error descargando la hoja:", r.stderr[-300:])
        sys.exit(1)
    print("📥 Hoja descargada →", CSV_TMP)


def importar_bd():
    r = subprocess.run(["python3", IMPORTADOR, CSV_TMP], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print("❌ Error importando:", r.stderr[-300:])
        sys.exit(1)


def predios_en_hoja():
    with open(CSV_TMP, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        return [], []
    header = [h.strip() for h in rows[0]]
    idx_predio = header.index("Predio") if "Predio" in header else 4
    nombres = set()
    for r in rows[1:]:
        if len(r) > idx_predio and r[idx_predio].strip():
            nombres.add(r[idx_predio].strip().upper())
    return nombres, header


def construir_fila(con, header, predio_nombre):
    """Construye la fila (89 columnas) en el orden real de la cabecera."""
    con.row_factory = sqlite3.Row
    p = con.execute("SELECT * FROM predios WHERE nombre=?", (predio_nombre,)).fetchone()
    if not p:
        return None
    a = con.execute("SELECT * FROM auditorias WHERE predio_id=? ORDER BY fecha DESC, id DESC LIMIT 1",
                    (p["id"],)).fetchone()
    if not a:
        return None
    resp = {r["criterio_id"]: r["respuesta"] for r in con.execute(
        "SELECT criterio_id, respuesta FROM respuestas WHERE auditoria_id=?", (a["id"],))}
    mapa = {"FCumplidos": "f_cumplidos", "FTotal": "f_total", "FPorcentaje": "f_pct",
            "MyCumplidos": "my_cumplidos", "MyTotal": "my_total", "MyPorcentaje": "my_pct",
            "MnCumplidos": "mn_cumplidos", "MnTotal": "mn_total", "MnPorcentaje": "mn_pct"}
    campos = {"Propietario": "propietario", "Identificación": "identificacion", "Teléfono": "telefono",
              "Email": "email", "Predio": "nombre", "Departamento": "departamento", "Municipio": "municipio",
              "Vereda": "vereda", "RSPP": "rspp", "Especie": "especie", "FinZootécnico": "fin_zootecnico",
              "Producción": "produccion"}
    fila = []
    for col in header:
        if col in campos:
            fila.append(p[campos[col]] or "")
        elif col in ("Latitud", "Longitud", "TotalAnimales"):
            v = p["latitud"] if col == "Latitud" else p["longitud"] if col == "Longitud" else p["total_animales"]
            fila.append(v if v is not None else "")
        elif col in mapa:
            fila.append(a[mapa[col]] if a[mapa[col]] is not None else "")
        elif col == "Concepto":
            fila.append(a["concepto"])
        elif col == "Observación":
            fila.append(a["observaciones"] or "")
        elif col == "Recomendación":
            fila.append(a["recomendaciones"] or "")
        else:  # C1.1|F ...
            fila.append(resp.get(col.split("|")[0].lstrip("C"), ""))
    return fila


def push(con, header, nombres_hoja):
    predios_bd = [r[0] for r in con.execute("SELECT DISTINCT nombre FROM predios ORDER BY nombre")]
    pendientes = [n for n in predios_bd if n not in nombres_hoja]
    if not pendientes:
        print("✅ Sin sincronizar: todos los predios de la BD ya tienen fila en la hoja.")
        return
    for nombre in pendientes:
        fila = construir_fila(con, header, nombre)
        if not fila:
            continue
        import subprocess as sp
        r = sp.run(GAPI + ["sheets", "append", SHEET, f"{TAB}!A1", "--values", json.dumps([fila])],
                   capture_output=True, text=True)
        if r.returncode == 0:
            print(f"📤 {nombre}: fila escrita en la hoja ✓")
        else:
            print(f"❌ {nombre}: {r.stderr[-250:]}")


def main():
    push_flag = "--push" in sys.argv
    pull_only = "--pull" in sys.argv
    descargar_hoja()
    importar_bd()
    if pull_only:
        return
    if push_flag or True:  # push por defecto
        con = sqlite3.connect(DB)
        nombres_hoja, header = predios_en_hoja()
        push(con, header, nombres_hoja)
        con.close()
    print("\n✅ Sincronización completada.")


if __name__ == "__main__":
    main()
