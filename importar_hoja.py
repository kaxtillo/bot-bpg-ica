#!/usr/bin/env python3
"""
Importa resultados de auditorías BPG desde un CSV exportado de la hoja de
cálculo de Google Sheets ("Auditoria BPG") a la base local de consolidación.

Regla clave (hoja SIN columna Fecha — caso real):
  Cada fila = ESTADO ACTUAL del predio. NO se crean auditorías nuevas por
  cada importación (eso generaba duplicados/corruptos). En su lugar se
  ACTUALIZA la auditoría más reciente del predio con el contenido de la hoja.
  Los % y el concepto se RECALCULAN desde las respuestas SI/NO/NA importadas
  (NA excluidos), con los umbrales oficiales F=100%, My>=80%, Mn>=60% — para
  no heredar porcentajes corruptos que la hoja pueda arrastrar.

Uso: python3 importar_hoja.py /ruta/hoja.csv
"""
import csv
import os
import re
import sqlite3
import sys
from datetime import date

DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")
UMBRALES = {"F": 100.0, "My": 80.0, "Mn": 60.0}


def parse_float(v):
    """Tolera '95.7', '2.454.843' (miles/decimal colombiano), '96,15'."""
    if v is None:
        return None
    s = str(v).strip().replace(",", ".").replace("%", "")
    if not s or s in ("-", "—"):
        return None
    if s.count(".") > 1:
        i = s.rfind(".")
        s = s[:i].replace(".", "") + s[i:]
    try:
        return float(s)
    except ValueError:
        return None


def normalizar_respuesta(v):
    if v is None:
        return None
    s = str(v).strip().upper()
    if s in ("N/A", "NA", "-", "—", "NO APLICA", "NP"):
        return "NA"
    if s in ("SI", "SÍ", "S", "1", "TRUE", "VERDADERO", "CUMPLE", "CUMPLE TOTALMENTE", "X"):
        return "SI"
    if s in ("NO", "N", "0", "FALSE", "FALSO", "NO CUMPLE", "INCUMPLE"):
        return "NO"
    return None


def recalcular_auditoria(con, aid, tipos):
    """Recalcula % y concepto de una auditoría desde sus respuestas."""
    resp = dict(con.execute(
        "SELECT criterio_id, respuesta FROM respuestas WHERE auditoria_id=?", (aid,)).fetchall())
    if not resp:
        return
    res = {}
    for t in ("F", "My", "Mn"):
        c = tot = 0
        for cid, tipo in tipos.items():
            r = resp.get(cid)
            if r == "SI" and tipo == t:
                c += 1; tot += 1
            elif r == "NO" and tipo == t:
                tot += 1
        res[t] = (c, tot, round(c / tot * 100, 2) if tot else 100.0)
    concepto = "Certificable" if all(res[t][2] >= UMBRALES[t] for t in ("F", "My", "Mn")) else "Aplazado"
    con.execute(
        """UPDATE auditorias SET concepto=?, f_cumplidos=?, f_total=?, f_pct=?,
           my_cumplidos=?, my_total=?, my_pct=?, mn_cumplidos=?, mn_total=?, mn_pct=?
           WHERE id=?""",
        (concepto, res["F"][0], res["F"][1], res["F"][2],
         res["My"][0], res["My"][1], res["My"][2],
         res["Mn"][0], res["Mn"][1], res["Mn"][2], aid))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    con = sqlite3.connect(DB)

    with open(path, newline="", encoding="utf-8-sig") as f:
        header = [h.strip() for h in (list(csv.reader(f))[0])]

    crit_cols = {}
    for col in header:
        m = re.match(r"^C(\d+)\.(\d+)\|(F|My|Mn)$", col) or re.match(
            r"^Crit_(\d+)_(\d+)_(F|My|Mn)$", col, re.IGNORECASE)
        if m:
            crit_cols[f"{int(m.group(1))}.{int(m.group(2))}"] = col

    if not crit_cols:
        print("❌ No se encontraron columnas de criterios en el CSV.")
        sys.exit(1)

    validos = {r[0] for r in con.execute("SELECT id FROM criterios")}
    tipos = dict(con.execute("SELECT id, tipo FROM criterios").fetchall())
    tiene_col_fecha = "Fecha" in header

    n_filas = n_nuevas = n_act = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for fila in csv.DictReader(f):
            predio_nombre = (fila.get("Predio") or "").strip().upper()
            if not predio_nombre:
                continue
            n_filas += 1
            concepto = (fila.get("Concepto") or "Sin concepto").strip()
            obs = fila.get("Observación") or fila.get("Observacion") or None
            rec = fila.get("Recomendación") or fila.get("Recomendacion") or None

            # --- upsert predio ---
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
                (predio_nombre, fila.get("Propietario") or None,
                 fila.get("Identificación") or fila.get("Identificacion") or None,
                 fila.get("Teléfono") or fila.get("Telefono") or None,
                 fila.get("Email") or None, fila.get("Departamento") or None,
                 fila.get("Municipio") or None, fila.get("Vereda") or None,
                 parse_float(fila.get("Latitud")), parse_float(fila.get("Longitud")),
                 fila.get("RSPP") or None, fila.get("Especie") or None,
                 fila.get("FinZootécnico") or fila.get("FinZootecnico") or None,
                 fila.get("Producción") or fila.get("Produccion") or None,
                 parse_float(fila.get("TotalAnimales")) or None))
            pid = con.execute("SELECT id FROM predios WHERE nombre=?", (predio_nombre,)).fetchone()[0]

            fecha = (fila.get("Fecha") or "").strip()

            if not fecha:
                # ESTADO ACTUAL: actualizar la auditoría más reciente del predio.
                ultima = con.execute(
                    "SELECT id FROM auditorias WHERE predio_id=? ORDER BY fecha DESC, id DESC LIMIT 1",
                    (pid,)).fetchone()
                if ultima:
                    aid = ultima[0]
                    con.execute("DELETE FROM respuestas WHERE auditoria_id=?", (aid,))
                    con.execute("UPDATE auditorias SET concepto=?, observaciones=?, recomendaciones=? WHERE id=?",
                                (concepto, obs, rec, aid))
                    modo = "actualizada"
                    n_act += 1
                else:
                    cur = con.execute(
                        "INSERT INTO auditorias (predio_id, fecha, concepto, observaciones, recomendaciones, fuente) "
                        "VALUES (?,?,?,?,?,?)",
                        (pid, date.today().isoformat(), concepto, obs, rec,
                         f"CSV {os.path.basename(path)}"))
                    aid = cur.lastrowid
                    modo = "nueva"
                    n_nuevas += 1
            elif tiene_col_fecha:
                # CON fecha: historial real, dedup por (predio, fecha, concepto).
                fecha_orig = (fila.get("Fecha") or "").strip()
                fecha = (fecha_orig[:10] if fecha_orig else date.today().isoformat())
                existente = con.execute(
                    "SELECT id FROM auditorias WHERE predio_id=? AND fecha=? AND concepto=?",
                    (pid, fecha, concepto)).fetchone()
                if existente:
                    aid = existente[0]
                    con.execute("DELETE FROM respuestas WHERE auditoria_id=?", (aid,))
                    modo = "actualizada"
                    n_act += 1
                else:
                    cur = con.execute(
                        "INSERT INTO auditorias (predio_id, fecha, concepto, observaciones, recomendaciones, fuente) "
                        "VALUES (?,?,?,?,?,?)",
                        (pid, fecha, concepto, obs, rec, f"CSV {os.path.basename(path)}"))
                    aid = cur.lastrowid
                    modo = "nueva"
                    n_nuevas += 1
            else:
                aid = None

            # --- respuestas por criterio ---
            n_resp = 0
            for cid, col in crit_cols.items():
                if cid not in validos:
                    continue
                resp = normalizar_respuesta(fila.get(col))
                if resp:
                    con.execute("INSERT INTO respuestas (auditoria_id, criterio_id, respuesta) VALUES (?,?,?)",
                                (aid, cid, resp))
                    n_resp += 1

            # RECALCULAR % y concepto desde respuestas (anti-% corruptos de la hoja)
            recalcular_auditoria(con, aid, tipos)
            fecha_mostrar = con.execute("SELECT fecha FROM auditorias WHERE id=?", (aid,)).fetchone()[0]
            concepto_final = con.execute("SELECT concepto FROM auditorias WHERE id=?", (aid,)).fetchone()[0]
            print(f"  [{modo}] {predio_nombre:14s} {fecha_mostrar} → {concepto_final} ({n_resp} respuestas)")

    con.commit()
    total_a = con.execute("SELECT COUNT(*) FROM auditorias").fetchone()[0]
    print()
    print(f"✅ Importación completa: {n_filas} fila(s), {n_nuevas} nueva(s), {n_act} actualizada(s)")
    print(f"   Total en BD: {con.execute('SELECT COUNT(*) FROM predios').fetchone()[0]} predios, {total_a} auditorías")
    con.close()


if __name__ == "__main__":
    main()
