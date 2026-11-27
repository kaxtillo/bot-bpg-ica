#!/usr/bin/env python3
"""
corregir_lopez_y_respuestas.py — Cirugía puntual:

1. Crea los predios de los hermanos López con numeral romano al final
   (LA ESPERANZA II y EL MANGO II), para no chocar con los predios homónimos.
2. Mueve la auditoría #57 a LA ESPERANZA II y le repone sus 62 respuestas
   desde el envío original de Kobo.
3. Crea la auditoría de EL MANGO II desde su envío.
4. Repone las respuestas de EL MANGO (#58) desde el envío del propietario real.
5. Repara las demás auditorías alteradas por la hoja (#68, #25, #50).

Uso:  corregir_lopez_y_respuestas.py [--aplicar]     (sin --aplicar solo muestra)
"""
import argparse, json, os, re, shutil, sqlite3, sys, unicodedata, urllib.request
from datetime import datetime

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
ENV = os.path.expanduser("~/.hermes/.env")
PAT = re.compile(r"seccion_\d+/c_(\d+)_(\d+)$")
MAPA = {"si": "SI", "no": "NO", "no_aplica": "NA", "na": "NA"}


def plano(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", plano(s).upper())


def envios():
    key = [l.split("=", 1)[1].strip() for l in open(ENV) if l.startswith("KOBO_TOKEN=")][0]
    q = urllib.request.Request(
        "https://kf.kobotoolbox.org/api/v2/assets/aNVGYKhswB8hFBSArTh8b8/data/?format=json&limit=400",
        headers={"Authorization": "Token " + key, "Accept": "application/json"})
    return {s["_id"]: s for s in json.load(urllib.request.urlopen(q, timeout=120))["results"]}


def patron(sub):
    o = {}
    for k, v in sub.items():
        m = PAT.match(k)
        if m:
            o[f"{int(m.group(1))}.{int(m.group(2))}"] = MAPA.get(str(v).strip().lower(), str(v).strip().upper())
    return o


def escribir_respuestas(con, aid, pat):
    con.execute("DELETE FROM respuestas WHERE auditoria_id=?", (aid,))
    for cid, val in sorted(pat.items(), key=lambda x: [int(p) for p in x[0].split(".")]):
        con.execute("INSERT INTO respuestas (auditoria_id, criterio_id, respuesta) VALUES (?,?,?)",
                    (aid, cid, val))
    return len(pat)


def recalcular(con, aid):
    tipos = dict(con.execute("SELECT id, tipo FROM criterios").fetchall())
    calc = {"F": [0, 0], "My": [0, 0], "Mn": [0, 0]}
    for cid, r in con.execute("SELECT criterio_id, respuesta FROM respuestas WHERE auditoria_id=?", (aid,)):
        t = tipos.get(cid)
        if t not in calc or r == "NA":
            continue
        calc[t][1] += 1
        if r == "SI":
            calc[t][0] += 1
    pct = {k: (v[0] / v[1] * 100 if v[1] else 0.0) for k, v in calc.items()}
    concepto = "Certificable" if (pct["F"] >= 100 and pct["My"] >= 80 and pct["Mn"] >= 60) else "Aplazado"
    con.execute("""UPDATE auditorias SET f_cumplidos=?, f_total=?, f_pct=?, my_cumplidos=?, my_total=?,
                   my_pct=?, mn_cumplidos=?, mn_total=?, mn_pct=?, concepto=? WHERE id=?""",
                (calc["F"][0], calc["F"][1], round(pct["F"], 2), calc["My"][0], calc["My"][1],
                 round(pct["My"], 2), calc["Mn"][0], calc["Mn"][1], round(pct["Mn"], 2), concepto, aid))
    return concepto, calc, pct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    aplicar = a.aplicar
    sub = envios()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    print("MODO:", "APLICAR" if aplicar else "simulación (usa --aplicar)")

    # ---------- 1. predios de los López ----------
    nuevos = [
        ("LA ESPERANZA II", "Sebastián David López Chandillo", "1007201493", "3164621987", "Primavera"),
        ("EL MANGO II", "Miguel Ángel López Chandillo", "1060805872", "3185907601", "Cenegueta"),
    ]
    ids = {}
    for nombre, prop, ced, tel, vereda in nuevos:
        existente = con.execute("SELECT id FROM predios WHERE UPPER(nombre)=?", (nombre,)).fetchone()
        if existente:
            ids[nombre] = existente[0]
            print(f"  · {nombre} ya existe (id {existente[0]})")
        elif aplicar:
            cur = con.execute("""INSERT INTO predios (nombre, propietario, identificacion, telefono, departamento,
                                 municipio, vereda) VALUES (?,?,?,?,'Cauca','Cajibío',?)""",
                              (nombre, prop, ced, tel, vereda))
            ids[nombre] = cur.lastrowid
            print(f"  + creado {nombre} (id {cur.lastrowid}) · {prop} · {ced} · Cajibío/{vereda}")
        else:
            print(f"  + crearía {nombre} · {prop} · {ced} · Cajibío/{vereda}")

    # ---------- 2. auditoría #57 → LA ESPERANZA II ----------
    aud57 = con.execute("SELECT id, predio_id, fecha FROM auditorias WHERE id=57").fetchone()
    if aud57:
        print(f"\n  auditoría #57 (fecha {aud57['fecha']}) → se mueve a LA ESPERANZA II")
        if aplicar and "LA ESPERANZA II" in ids:
            con.execute("UPDATE auditorias SET predio_id=?, fuente='bot auditoria' WHERE id=57", (ids["LA ESPERANZA II"],))
            con.execute("UPDATE seguimiento SET predio_id=? WHERE auditoria_id=57", (ids["LA ESPERANZA II"],))
            n = escribir_respuestas(con, 57, patron(sub[918964016]))
            print(f"    respuestas repuestas desde el envío de López: {n}")

    # ---------- 3. auditoría nueva para EL MANGO II ----------
    if aplicar and "EL MANGO II" in ids:
        pid = ids["EL MANGO II"]
        ya = con.execute("SELECT id FROM auditorias WHERE predio_id=? AND fecha='2026-11-19'", (pid,)).fetchone()
        if ya:
            aid = ya[0]
            print(f"\n  EL MANGO II ya tiene auditoría del 19/11 (#{aid}); se repone")
        else:
            cur = con.execute("""INSERT INTO auditorias (predio_id, fecha, concepto, fuente)
                                 VALUES (?, '2026-11-19', 'Aplazado', 'bot auditoria')""", (pid,))
            aid = cur.lastrowid
            print(f"\n  + auditoría #{aid} creada para EL MANGO II (2026-11-19)")
        n = escribir_respuestas(con, aid, patron(sub[918964024]))
        concepto, calc, pct = recalcular(con, aid)
        print(f"    respuestas: {n} · {concepto} · F {calc['F'][0]}/{calc['F'][1]}={pct['F']:.1f}% "
              f"My {pct['My']:.1f}% Mn {pct['Mn']:.1f}%")
    else:
        print(f"\n  + crearía la auditoría 2026-11-19 de EL MANGO II desde el envío {918964024}")

    # ---------- 4. y 5. reparaciones por envío conocido ----------
    reparar = [
        (58, 919206994, "EL MANGO (propietario real, 19/11)"),
        (68, 923188020, "EL ENCANTO (19/11)"),
    ]
    print()
    for aid, sid, etiqueta in reparar:
        fila = con.execute("SELECT id FROM auditorias WHERE id=?", (aid,)).fetchone()
        if not fila:
            print(f"  # {aid} no existe ({etiqueta})")
            continue
        p = patron(sub[sid])
        if aplicar:
            n = escribir_respuestas(con, aid, p)
            concepto, calc, pct = recalcular(con, aid)
            print(f"  ✓ #{aid} {etiqueta}: {n} respuestas · {concepto} · "
                  f"F {calc['F'][0]}/{calc['F'][1]}={pct['F']:.1f}% My {pct['My']:.1f}% Mn {pct['Mn']:.1f}%")
        else:
            print(f"  · repararía #{aid} {etiqueta} con {len(p)} respuestas del envío {sid}")

    # ---------- 6. reparación automática del resto (nombre+fecha único) ----------
    print("\n  resto de auditorías: buscando envío único por nombre+fecha")
    for aud in con.execute("SELECT a.id,a.fecha,p.nombre FROM auditorias a JOIN predios p ON p.id=a.predio_id").fetchall():
        if aud["id"] in (57, 58, 68):
            continue
        bd = dict(con.execute("SELECT criterio_id,respuesta FROM respuestas WHERE auditoria_id=?", (aud["id"],)))
        if len(bd) < 50:
            continue
        cands = [s for s in sub.values()
                 if norm(s.get("nombre_predio")) == norm(aud["nombre"]) and str(s.get("fecha"))[:10] == aud["fecha"]]
        if len(cands) != 1:
            continue
        p = patron(cands[0])
        dif = [c for c in bd if c in p and bd[c] != p[c]]
        if not dif:
            continue
        if aplicar:
            n = escribir_respuestas(con, aud["id"], p)
            concepto, calc, pct = recalcular(con, aud["id"])
            print(f"  ✓ #{aud['id']} {aud['nombre']} ({aud['fecha']}): {len(dif)} criterios corregidos · {concepto} "
                  f"F {calc['F'][0]}/{calc['F'][1]}={pct['F']:.1f}%")
        else:
            print(f"  · corregiría #{aud['id']} {aud['nombre']} ({aud['fecha']}): {len(dif)} criterios")

    if aplicar:
        con.commit()
        print("\n  cambios guardados")
    else:
        print("\n  simulación: no se guardó nada")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
