#!/usr/bin/env python3
"""
Importa resultados de auditorías BPG desde un CSV exportado de la hoja de
cálculo de Google Sheets ("Auditoria BPG") a la base local de consolidación.

Columnas esperadas (orden del Formato_Auditoria_BPG_62Criterios):
  Fecha, Propietario, Identificación, Teléfono, Email, Predio, Departamento,
  Municipio, Vereda, Latitud, Longitud, RSPP, Especie, FinZootécnico,
  Producción, TotalAnimales, Crit_1_1_F ... Crit_10_2_Mn (62),
  FCumplidos, FTotal, FPorcentaje, MyCumplidos, MyTotal, MyPorcentaje,
  MnCumplidos, MnTotal, MnPorcentaje, Concepto, Observación, Recomendación

Uso: python3 importar_hoja.py /ruta/hoja.csv
"""
import csv
import os
import re
import sqlite3
import sys
from datetime import date

DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")

TIPO_MAP = {"F": "F", "My": "My", "Mn": "Mn"}


def parse_float(v):
    """Tolera formatos: '95.7', '2.454.843' (colombiano: puntos de miles y decimal),
    '96,15'. Regla: si hay >1 punto, el último es el decimal y los demás son miles."""
    if v is None:
        return None
    s = str(v).strip().replace(",", ".").replace("%", "")
    if not s or s in ("-", "—", ""):
        return None
    n = s.count(".")
    if n > 1:
        # último punto = decimal; quitar los anteriores
        i = s.rfind(".")
        s = s[:i].replace(".", "") + s[i:]
    try:
        return float(s)
    except ValueError:
        return None


def normalizar_respuesta(v):
    """Tolera SI/Sí/1/Cumple/TRUE → SI; NO/0/No cumple/FALSE → NO; NA/N-A/— → NA."""
    if v is None:
        return None
    s = str(v).strip().upper()
    if s in ("SI", "SÍ", "S", "1", "TRUE", "VERDADERO", "CUMPLE", "CUMPLE TOTALMENTE", "X"):
        return "SI"
    if s in ("NO", "N", "0", "FALSE", "FALSO", "NO CUMPLE", "INCUMPLE", "N/A", "NA"):
        # 'N/A' y 'NA' son No Aplica → NA
        if s in ("N/A", "NA"):
            return "NA"
        return "NO"
    if s in ("NA", "N/A", "-", "—", "NO APLICA", "NP"):
        return "NA"
    return None


def parse_float_legacy(v):
    try:
        return float(str(v).replace(",", ".").replace("%", "").strip())
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    con = sqlite3.connect(DB)

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = [h.strip() for h in (reader.fieldnames or [])]

    # índice de columnas de criterios: C1.1|F  o  Crit_1_1_F
    crit_cols = {}
    for col in header:
        m = re.match(r"^C(\d+)\.(\d+)\|(F|My|Mn)$", col) or re.match(
            r"^Crit_(\d+)_(\d+)_(F|My|Mn)$", col, re.IGNORECASE
        )
        if m:
            crit_cols[f"{int(m.group(1))}.{int(m.group(2))}"] = col

    if not crit_cols:
        print("❌ No se encontraron columnas Crit_X_Y_Z en el CSV. ¿Es el archivo correcto?")
        sys.exit(1)

    validos = {r[0] for r in con.execute("SELECT id FROM criterios")}
    n_filas = 0
    n_nuevas = 0
    n_act = 0

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            predio_nombre = (fila.get("Predio") or "").strip().upper()
            if not predio_nombre:
                continue
            n_filas += 1

            # upsert predio
            con.execute(
                """INSERT INTO predios (nombre, propietario, identificacion, telefono, email,
                   departamento, municipio, vereda, latitud, longitud, rspp, especie, fin_zootecnico,
                   produccion, total_animales)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(nombre) DO UPDATE SET propietario=excluded.propietario,
                     identificacion=excluded.identificacion, telefono=excluded.telefono,
                     email=excluded.email, departamento=excluded.departamento,
                     municipio=excluded.municipio, vereda=excluded.vereda,
                     latitud=excluded.latitud, longitud=excluded.longitud, rspp=excluded.rspp,
                     especie=excluded.especie, fin_zootecnico=excluded.fin_zootecnico,
                     produccion=excluded.produccion, total_animales=excluded.total_animales""",
                (
                    predio_nombre,
                    fila.get("Propietario") or None,
                    fila.get("Identificación") or fila.get("Identificacion") or None,
                    fila.get("Teléfono") or fila.get("Telefono") or None,
                    fila.get("Email") or None,
                    fila.get("Departamento") or None,
                    fila.get("Municipio") or None,
                    fila.get("Vereda") or None,
                    parse_float(fila.get("Latitud")),
                    parse_float(fila.get("Longitud")),
                    fila.get("RSPP") or None,
                    fila.get("Especie") or None,
                    fila.get("FinZootécnico") or fila.get("FinZootecnico") or None,
                    fila.get("Producción") or fila.get("Produccion") or None,
                    parse_float(fila.get("TotalAnimales")) or None,
                ),
            )
            pid = con.execute("SELECT id FROM predios WHERE nombre=?", (predio_nombre,)).fetchone()[0]

            fecha = (fila.get("Fecha") or "").strip()
            concepto = (fila.get("Concepto") or "Sin concepto").strip()
            if not fecha:
                # La hoja real no tiene columna Fecha: reutilizar la fecha de una
                # auditoría previa del predio con el mismo concepto (evita
                # duplicar), o usar hoy si es la primera vez.
                prev = con.execute(
                    """SELECT a.fecha FROM auditorias a JOIN predios p ON p.id=a.predio_id
                       WHERE p.nombre=? AND a.concepto=? ORDER BY a.fecha DESC LIMIT 1""",
                    (predio_nombre, concepto),
                ).fetchone()
                fecha = prev[0] if prev else date.today().isoformat()

            # ¿la auditoría ya existe? (mismo predio+fecha+concepto → actualizar)
            existente = con.execute(
                """SELECT id FROM auditorias WHERE predio_id=? AND fecha=? AND concepto=?""",
                (pid, fecha, concepto),
            ).fetchone()
            if existente:
                aid = existente[0]
                con.execute("DELETE FROM respuestas WHERE auditoria_id=?", (aid,))
                modo = "actualizada"
                n_act += 1
            else:
                cur = con.execute(
                    """INSERT INTO auditorias (predio_id, fecha, concepto, f_cumplidos, f_total, f_pct,
                       my_cumplidos, my_total, my_pct, mn_cumplidos, mn_total, mn_pct,
                       observaciones, recomendaciones, fuente)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        pid, fecha, concepto,
                        parse_float(fila.get("FCumplidos")), parse_float(fila.get("FTotal")),
                        parse_float(fila.get("FPorcentaje")),
                        parse_float(fila.get("MyCumplidos")), parse_float(fila.get("MyTotal")),
                        parse_float(fila.get("MyPorcentaje")),
                        parse_float(fila.get("MnCumplidos")), parse_float(fila.get("MnTotal")),
                        parse_float(fila.get("MnPorcentaje")),
                        fila.get("Observación") or fila.get("Observacion") or None,
                        fila.get("Recomendación") or fila.get("Recomendacion") or None,
                        f"CSV {os.path.basename(path)}",
                    ),
                )
                aid = cur.lastrowid
                modo = "nueva"
                n_nuevas += 1

            # respuestas por criterio
            n_resp = 0
            for cid, col in crit_cols.items():
                if cid not in validos:
                    continue
                resp = normalizar_respuesta(fila.get(col))
                if resp:
                    con.execute(
                        "INSERT INTO respuestas (auditoria_id, criterio_id, respuesta) VALUES (?,?,?)",
                        (aid, cid, resp),
                    )
                    n_resp += 1
            print(f"  [{modo}] {predio_nombre:14s} {fecha} → {concepto} ({n_resp} respuestas)")

    con.commit()
    print()
    print(f"✅ Importación completa: {n_filas} fila(s), {n_nuevas} nueva(s), {n_act} actualizada(s)")
    print(f"   Total en BD: {con.execute('SELECT COUNT(*) FROM predios').fetchone()[0]} predios, "
          f"{con.execute('SELECT COUNT(*) FROM auditorias').fetchone()[0]} auditorías")
    con.close()


if __name__ == "__main__":
    main()
