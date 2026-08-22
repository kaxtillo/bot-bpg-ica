#!/usr/bin/env python3
"""
Recalcula TODAS las auditorías de la BD con los umbrales oficiales de la
Forma 3-852 V6 (F = 100%, My ≥ 80%, Mn ≥ 60%) y actualiza concepto y %.
Usa las respuestas SI/NO/NA almacenadas (NA excluidos del denominador).
"""
import os
import sqlite3

DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")
UMBRALES = {"F": 100.0, "My": 80.0, "Mn": 60.0}


def main():
    con = sqlite3.connect(DB)
    # tipo por criterio
    tipos = dict(con.execute("SELECT id, tipo FROM criterios").fetchall())

    auditorias = con.execute("SELECT id, predio_id FROM auditorias ORDER BY id").fetchall()
    cambios = []
    for aid, pid in auditorias:
        resp = dict(con.execute(
            "SELECT criterio_id, respuesta FROM respuestas WHERE auditoria_id=?", (aid,)
        ).fetchall())
        if not resp:
            continue
        res = {}
        for t in ("F", "My", "Mn"):
            c = t_ = 0
            for cid, tipo in tipos.items():
                r = resp.get(cid)
                if r == "SI" and tipo == t:
                    c += 1
                    t_ += 1
                elif r == "NO" and tipo == t:
                    t_ += 1
            res[t] = (c, t_, round(c / t_ * 100, 2) if t_ else 100.0)

        concepto = "Certificable" if all(
            res[t][2] >= UMBRALES[t] for t in ("F", "My", "Mn")
        ) else "Aplazado"

        prev = con.execute(
            "SELECT concepto, f_cumplidos, f_total, f_pct, my_cumplidos, my_total, my_pct, mn_cumplidos, mn_total, mn_pct "
            "FROM auditorias WHERE id=?", (aid,)
        ).fetchone()
        con.execute(
            """UPDATE auditorias SET concepto=?, f_cumplidos=?, f_total=?, f_pct=?,
               my_cumplidos=?, my_total=?, my_pct=?, mn_cumplidos=?, mn_total=?, mn_pct=?
               WHERE id=?""",
            (concepto, res["F"][0], res["F"][1], res["F"][2],
             res["My"][0], res["My"][1], res["My"][2],
             res["Mn"][0], res["Mn"][1], res["Mn"][2], aid),
        )
        nombre = con.execute("SELECT nombre FROM predios WHERE id=?", (pid,)).fetchone()[0]
        if prev and prev[0] != concepto:
            cambios.append((nombre, prev[0], concepto, prev[3], res["F"][2], prev[5], res["My"][2]))
        print(f"  #{aid} {nombre:14s} → {concepto:12s} | F {res['F'][0]}/{res['F'][1]} ({res['F'][2]}%) · "
              f"My {res['My'][0]}/{res['My'][1]} ({res['My'][2]}%) · Mn {res['Mn'][0]}/{res['Mn'][1]} ({res['Mn'][2]}%)")

    con.commit()
    con.close()
    print()
    if cambios:
        print("🔴 CAMBIOS DE CONCEPTO:")
        for nombre, antes, despues, fp_ant, fp_nue, myp_ant, myp_nue in cambios:
            print(f"  • {nombre}: {antes} → {despues}  (F {fp_ant}% → {fp_nue}%, My {myp_ant}% → {myp_nue}%)")
    else:
        print("✅ Ningún concepto cambió.")


if __name__ == "__main__":
    main()
