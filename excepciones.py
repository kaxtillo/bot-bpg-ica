#!/usr/bin/env python3
"""
excepciones.py — Criterios que NO aplican a un predio concreto, de forma permanente.

Problema que resuelve: hay criterios que no aplican a ciertos predios (p. ej. Instalaciones
de Ordeño Móvil en un predio con ordeño fijo). Si solo se marca NA en la base, la siguiente
importación desde KoboToolbox o desde la hoja lo vuelve a dejar en NO y el predio aparece
aplazado otra vez. Aquí la excepción queda registrada en la tabla `excepciones` y se
re-aplica después de cada importación.

Uso:
    excepciones.py --marcar "LA GUACA" 4.3 --motivo "Ordeño fijo: no tiene ordeño móvil"
    excepciones.py --aplicar          # re-aplica todas (idempotente; va en sincronizar_todo.sh)
    excepciones.py --listar
    excepciones.py --quitar 4.3 "LA GUACA"
"""
import argparse, os, sqlite3, sys
from datetime import date

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
UMBRAL = {"F": 100.0, "My": 80.0, "Mn": 60.0}


def crear_tabla(con):
    con.execute("""CREATE TABLE IF NOT EXISTS excepciones (
        predio_id INTEGER NOT NULL REFERENCES predios(id),
        criterio_id TEXT NOT NULL REFERENCES criterios(id),
        motivo TEXT,
        creado_en TEXT,
        PRIMARY KEY (predio_id, criterio_id))""")


def recalcular(con, aid):
    tipos = dict(con.execute("SELECT id, tipo FROM criterios").fetchall())
    calc = {"F": [0, 0], "My": [0, 0], "Mn": [0, 0]}
    for cid, r in con.execute("SELECT criterio_id, respuesta FROM respuestas WHERE auditoria_id=?", (aid,)):
        t = tipos.get(cid)
        if t in calc and r != "NA":
            calc[t][1] += 1
            if r == "SI":
                calc[t][0] += 1
    pct = {k: (v[0] / v[1] * 100 if v[1] else 0.0) for k, v in calc.items()}
    concepto = "Certificable" if all(pct[k] >= UMBRAL[k] for k in UMBRAL) else "Aplazado"
    con.execute("""UPDATE auditorias SET f_cumplidos=?, f_total=?, f_pct=?, my_cumplidos=?, my_total=?,
                   my_pct=?, mn_cumplidos=?, mn_total=?, mn_pct=?, concepto=? WHERE id=?""",
                (calc["F"][0], calc["F"][1], round(pct["F"], 2), calc["My"][0], calc["My"][1],
                 round(pct["My"], 2), calc["Mn"][0], calc["Mn"][1], round(pct["Mn"], 2), concepto, aid))
    return concepto, calc, pct


def aplicar(con, verbose=True):
    """Marca como NA las respuestas de los criterios exceptuados en la última auditoría."""
    crear_tabla(con)
    excep = con.execute("""SELECT e.predio_id, e.criterio_id, e.motivo, p.nombre
                           FROM excepciones e JOIN predios p ON p.id=e.predio_id""").fetchall()
    cambios = 0
    for pid, cid, motivo, nombre in excep:
        aud = con.execute("""SELECT id FROM auditorias WHERE predio_id=?
                             ORDER BY fecha DESC, id DESC LIMIT 1""", (pid,)).fetchone()
        if not aud:
            continue
        aid = aud[0]
        actual = con.execute("SELECT respuesta FROM respuestas WHERE auditoria_id=? AND criterio_id=?",
                             (aid, cid)).fetchone()
        if actual and actual[0] == "NA":
            continue
        if actual:
            con.execute("UPDATE respuestas SET respuesta='NA' WHERE auditoria_id=? AND criterio_id=?", (aid, cid))
        else:
            con.execute("INSERT INTO respuestas (auditoria_id, criterio_id, respuesta) VALUES (?,?,'NA')", (aid, cid))
        concepto, calc, pct = recalcular(con, aid)
        cambios += 1
        if verbose:
            print(f"  ✓ {nombre}: {cid} → NA ({motivo}) · auditoría #{aid} queda {concepto} "
                  f"F {calc['F'][0]}/{calc['F'][1]}={pct['F']:.1f}% My {pct['My']:.1f}% Mn {pct['Mn']:.1f}%")
    con.commit()
    if verbose and not cambios:
        print(f"  {len(excep)} excepción(es) registradas; todas ya estaban aplicadas")
    return cambios


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--marcar", nargs=2, metavar=("PREDIO", "CRITERIO"))
    ap.add_argument("--motivo", default="")
    ap.add_argument("--quitar", nargs=2, metavar=("CRITERIO", "PREDIO"))
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    crear_tabla(con)

    if a.listar or not (a.marcar or a.quitar or a.aplicar):
        print("Excepciones registradas (criterios que no aplican a un predio):")
        filas = con.execute("""SELECT p.nombre, e.criterio_id, c.nombre, e.motivo, e.creado_en
                               FROM excepciones e JOIN predios p ON p.id=e.predio_id
                               LEFT JOIN criterios c ON c.id=e.criterio_id ORDER BY p.nombre""").fetchall()
        if not filas:
            print("  (ninguna)")
        for n, cid, cn, mot, f in filas:
            print(f"  {n:<22} {cid:<6} {cn or '':<40} {mot}  [{f}]")
        return 0

    if a.marcar:
        predio, criterio = a.marcar
        r = con.execute("SELECT id FROM predios WHERE UPPER(TRIM(nombre))=UPPER(TRIM(?))", (predio,)).fetchone()
        if not r:
            print("  ✗ no existe el predio", predio); return 1
        if not con.execute("SELECT 1 FROM criterios WHERE id=?", (criterio,)).fetchone():
            print("  ✗ no existe el criterio", criterio); return 1
        con.execute("""INSERT INTO excepciones (predio_id, criterio_id, motivo, creado_en) VALUES (?,?,?,?)
                       ON CONFLICT(predio_id, criterio_id) DO UPDATE SET motivo=excluded.motivo""",
                    (r[0], criterio, a.motivo, date.today().isoformat()))
        con.commit()
        print(f"  ✓ registrada: {predio} · criterio {criterio} no aplica ({a.motivo})")

    if a.quitar:
        criterio, predio = a.quitar
        con.execute("""DELETE FROM excepciones WHERE criterio_id=?
                       AND predio_id=(SELECT id FROM predios WHERE UPPER(TRIM(nombre))=UPPER(TRIM(?)))""",
                    (criterio, predio))
        con.commit()
        print(f"  ✓ eliminada la excepción {criterio} de {predio}")

    if a.aplicar:
        print("Aplicando excepciones…")
        aplicar(con)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
