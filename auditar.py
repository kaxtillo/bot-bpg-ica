#!/usr/bin/env python3
"""
Auditoría BPG ICA (Res. 067449) — 100% LOCAL, sin IA online.

Modo interactivo (terminal):
  python3 auditar.py
  → pide los 7 datos del predio y las 62 preguntas una a una (SI/NO/NA),
    calcula, guarda en la BD y muestra el reporte.

Modo archivo (formulario llenado en campo, ver generar_formulario.py):
  python3 auditar.py --archivo formulario.csv
  → procesa el CSV con las respuestas y guarda.

Ctrl+C en cualquier momento guarda el progreso parcial.
"""
import csv
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date

DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")
GUARDAR = os.path.expanduser("~/auditorias_bpg/guardar_auditoria.py")

CAMPOS_REGISTRO = [
    ("predio", "Nombre del predio", True),
    ("propietario", "Nombre del propietario", True),
    ("identificacion", "Cédula del propietario", False),
    ("municipio", "Municipio", True),
    ("vereda", "Vereda", False),
    ("telefono", "Teléfono", False),
    ("gps", "Coordenadas GPS (lat, lon) — o 'no'", False),
]

VALIDA = {"SI", "NO", "NA"}
SINONIMOS = {
    "s": "SI", "si": "SI", "sí": "SI", "1": "SI", "cumple": "SI", "x": "SI",
    "n": "NO", "no": "NO", "0": "NO", "no cumple": "NO",
    "na": "NA", "n/a": "NA", "-": "NA", "no aplica": "NA", "no aplica ": "NA",
}


def normalizar(resp):
    r = resp.strip().upper()
    if r in VALIDA:
        return r
    return SINONIMOS.get(r.strip().lower())


def criterios(con):
    return con.execute(
        """SELECT id, nombre, tipo, articulo, pregunta FROM criterios
           ORDER BY CAST(substr(id,1,instr(id,'.')-1) AS INT), CAST(substr(id,instr(id,'.')+1) AS INT)"""
    ).fetchall()


def pedir_registro():
    datos = {}
    print("═" * 56)
    print("  📋 AUDITORÍA BPG ICA — Res. 067449 (modo local)")
    print("═" * 56)
    print("  Registro inicial del predio:\n")
    for campo, etiqueta, req in CAMPOS_REGISTRO:
        while True:
            v = input(f"  {etiqueta}: ").strip()
            if v:
                break
            if not req:
                continue
            print("    ⚠️  Este dato es obligatorio.")
        if campo == "gps" and v.lower() in ("no", "n", "-", ""):
            v = ""
        datos[campo] = v
        if campo == "gps" and v:
            try:
                lat, lon = v.replace(" ", "").split(",")
                datos["latitud"], datos["longitud"] = float(lat), float(lon)
            except Exception:
                datos["latitud"] = datos["longitud"] = None
    return datos


def correr_cuestionario(con):
    lista = criterios(con)
    total = len(lista)
    detalle = {}
    print("\n" + "═" * 56)
    print(f"  Cuestionario — {total} criterios. Responda SI / NO / NA")
    print("═" * 56)
    for i, (cid, nombre, tipo, art, pregunta) in enumerate(lista, 1):
        while True:
            try:
                r = input(f"\n  [{i}/{total}] {cid} {nombre.upper()} ({tipo} - Art. {art})\n  {pregunta}\n  → ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\n  ⏸️  Progreso guardado parcialmente. Puede retomar luego.")
                guardar_parcial(detalle)
                sys.exit(130)
            norm = normalizar(r)
            if norm:
                detalle[cid] = norm
                break
            print("    ⚠️  Responda: SI / NO / NA")
    return detalle


def guardar_parcial(detalle):
    if not detalle:
        return
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS progreso_parcial (criterio_id TEXT PRIMARY KEY, respuesta TEXT)")
    con.executemany("INSERT OR REPLACE INTO progreso_parcial VALUES (?,?)", detalle.items())
    con.commit()
    con.close()
    print(f"    💾 {len(detalle)} respuestas guardadas en progreso_parcial (BD local)")


def leer_formulario(path):
    """Lee el CSV vertical de generar_formulario.py → (datos_predio, detalle)."""
    con = sqlite3.connect(DB)
    validos = {c[0] for c in criterios(con)}
    con.close()
    datos = {}
    detalle = {}
    import re as _re
    pat = _re.compile(r"^\d+\.\d+$")
    with open(path, newline="", encoding="utf-8-sig") as f:
        for fila in csv.reader(f):
            if not fila or not fila[0]:
                continue
            sec = fila[0].strip()
            if sec == "predio" and len(fila) >= 3:
                campo = fila[1].replace("predio_", "").strip()
                valor = fila[2].strip()
                if campo and valor:
                    datos[campo] = valor
            elif pat.match(sec) and len(fila) >= 6:
                resp = normalizar(fila[5])
                if resp:
                    detalle[sec] = resp
    if "gps" in datos and datos["gps"]:
        try:
            lat, lon = datos["gps"].replace(" ", "").split(",")
            datos["latitud"], datos["longitud"] = float(lat), float(lon)
        except Exception:
            pass
    if not detalle:
        print("❌ No se encontraron respuestas en el formulario.")
        sys.exit(1)
    return datos, detalle


def main():
    con = sqlite3.connect(DB)
    if con.execute("SELECT COUNT(*) FROM criterios").fetchone()[0] < 62:
        print("❌ La BD no tiene los 62 criterios. Ejecute: python3 crear_bd.py")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--archivo":
        path = sys.argv[2]
        datos, detalle = leer_formulario(path)
        print(f"📄 Formulario leído: {len(detalle)} respuestas")
    else:
        datos = pedir_registro()
        detalle = correr_cuestionario(con)
    con.close()

    # completar datos del predio para el JSON de guardar_auditoria.py
    payload = {
        "predio": datos.get("predio", "").upper(),
        "propietario": datos.get("propietario", ""),
        "identificacion": datos.get("identificacion", ""),
        "telefono": datos.get("telefono", ""),
        "departamento": datos.get("departamento", "Cauca"),
        "municipio": datos.get("municipio", ""),
        "vereda": datos.get("vereda", ""),
        "latitud": datos.get("latitud"),
        "longitud": datos.get("longitud"),
        "especie": datos.get("especie", ""),
        "fin_zootecnico": datos.get("fin_zootecnico", ""),
        "fecha": date.today().isoformat(),
        "detalle_puntos": detalle,
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        tmp = f.name
    subprocess.run([sys.executable, GUARDAR, tmp], check=True)
    os.unlink(tmp)


if __name__ == "__main__":
    main()
