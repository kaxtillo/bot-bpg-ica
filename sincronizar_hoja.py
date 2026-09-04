#!/usr/bin/env python3
"""
Sincronización bidireccional entre la hoja de Google Sheets
("Auditorias BPG ICA - Produccion de Leche") y la base local.

1. Descarga la hoja a CSV y consolida en la BD local (importar_hoja.py).
2. PUSH BD→hoja:
   - Predios de la BD SIN fila en la hoja  → append (nueva fila).
   - Predios de la BD QUE YA tienen fila   → compara contenido y actualiza
     la fila si difiere (concepto, %, datos) — para que la hoja nunca quede
     desactualizada con conceptos/porcentajes viejos.

Uso: python3 sincronizar_hoja.py [--push] [--pull]
"""
import csv
import json
import os
import sqlite3
import subprocess
import sys

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


def leer_csv():
    """Devuelve (header, filas). Cada fila i (0-based) corresponde a la fila i+1 de la hoja."""
    with open(CSV_TMP, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        return [], []
    return [h.strip() for h in rows[0]], rows[1:]


def construir_fila(con, header, predio_nombre):
    """Construye la fila completa en el orden real de la cabecera."""
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
            fila.append(str(p[campos[col]] or ""))
        elif col in ("Latitud", "Longitud", "TotalAnimales"):
            v = p["latitud"] if col == "Latitud" else p["longitud"] if col == "Longitud" else p["total_animales"]
            fila.append(str(v).replace(".", ",") if v is not None and isinstance(v, float) else ("" if v is None else str(v)))
        elif col in mapa:
            v = a[mapa[col]]
            fila.append(str(v).replace(".", ",") if isinstance(v, float) else ("" if v is None else str(v)))
        elif col == "Concepto":
            fila.append(str(a["concepto"] or ""))
        elif col == "Observación":
            fila.append(str(a["observaciones"] or ""))
        elif col == "Recomendación":
            fila.append(str(a["recomendaciones"] or ""))
        else:  # C1.1|F ...
            fila.append(resp.get(col.split("|")[0].lstrip("C"), ""))
    return fila


def filas_por_predio():
    """Lee la hoja vía API y devuelve {NOMBRE_UPPER: numero_fila_real}."""
    r = subprocess.run(GAPI + ["sheets", "get", SHEET, f"{TAB}!A1:CK300"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("❌ No se pudo leer la hoja:", r.stderr[-250:])
        return {}
    data = json.loads(r.stdout)
    # localizar columna Predio (por header)
    header = data[0] if data else []
    ip = None
    for i, h in enumerate(header):
        if str(h).strip().lower() == "predio":
            ip = i
            break
    if ip is None:
        ip = 4
    mapa = {}
    for i, row in enumerate(data[1:], start=2):  # fila real de hoja = i
        if len(row) > ip and str(row[ip]).strip():
            mapa[str(row[ip]).strip().upper()] = i
    return mapa


def norm(v):
    """Normaliza un valor para comparar (números con coma colombiana)."""
    if v is None:
        return ""
    s = str(v).strip()
    try:
        return str(float(s.replace(",", ".")))
    except ValueError:
        return s.upper()


def push(con, header, fila_predio):
    """Agrega los faltantes y ACTUALIZA las filas existentes que difieren."""
    con.row_factory = sqlite3.Row
    predios = [r[0] for r in con.execute("SELECT DISTINCT nombre FROM predios ORDER BY nombre")]
    # filas actuales de la hoja (nombre → contenido) desde el CSV descargado
    _, csv_rows = leer_csv()
    # mapa nombre→(numero_fila_real, contenido) del CSV: csv fila i (0-based) = hoja fila i+2
    contenido_hoja = {}
    ip = header.index("Predio") if "Predio" in header else 4
    for i, r in enumerate(csv_rows):
        if len(r) > ip and r[ip].strip():
            contenido_hoja[r[ip].strip().upper()] = (i + 2, r)  # +2: +1 header del csv, +1 0-based

    updates = []   # batchUpdate de filas a corregir
    nuevos = []    # predios a agregar (append)
    for nombre in predios:
        fila = construir_fila(con, header, nombre)
        if not fila:
            continue
        key = nombre.upper()
        if key in fila_predio and key in contenido_hoja:
            num_fila, vieja = contenido_hoja[key]
            # comparar columnas presentes en ambas
            difiere = False
            for ci in range(min(len(fila), len(vieja))):
                if norm(fila[ci]) != norm(vieja[ci]):
                    difiere = True
                    break
            if not difiere and len(fila) != len(vieja):
                difiere = True
            if difiere:
                updates.append({"range": f"{TAB}!A{num_fila}:CK{num_fila}",
                                "values": [fila]})
        else:
            nuevos.append(fila)

    # aplicar actualizaciones (update por rango, ya que google_api no tiene batch)
    if updates:
        ok = 0
        for u in updates:
            r = subprocess.run(GAPI + ["sheets", "update", SHEET, u["range"],
                                       "--values", json.dumps(u["values"])],
                               capture_output=True, text=True)
            if r.returncode == 0:
                ok += 1
            else:
                print("❌ update", u["range"], ":", r.stderr[-200:])
        print(f"🔄 {ok}/{len(updates)} fila(s) actualizada(s) en la hoja (concepto/% corregidos)")
    # agregar nuevos
    for fila in nuevos:
        r = subprocess.run(GAPI + ["sheets", "append", SHEET, f"{TAB}!A1", "--values", json.dumps([fila])],
                           capture_output=True, text=True)
        if r.returncode == 0:
            print(f"📤 Fila agregada (predio en BD sin fila)")
        else:
            print(f"❌ append: {r.stderr[-250:]}")
    if not updates and not nuevos:
        print("✅ Sin cambios: BD y hoja sincronizadas (nada por agregar o corregir).")


def main():
    pull_only = "--pull" in sys.argv
    descargar_hoja()
    importar_bd()
    if pull_only:
        return
    con = sqlite3.connect(DB)
    header, _ = leer_csv()
    fila_predio = filas_por_predio()
    push(con, header, fila_predio)
    con.close()
    print("\n✅ Sincronización completada.")


if __name__ == "__main__":
    main()
