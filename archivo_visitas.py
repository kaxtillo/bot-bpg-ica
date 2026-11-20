#!/usr/bin/env python3
"""
archivo_visitas.py — Guarda visitas anteriores de un predio en una tabla de ARCHIVO,
sin que afecten lo que se muestra en el dashboard / mapa / planes.

Motivo: cuando un predio tiene varias visitas con la MISMA fecha de auditoría, la
consolidación normal las trata como duplicadas y descarta una. Decisión del auditor
(2026): conservar las dos, pero mostrar solo la más reciente.

Uso:
  archivo_visitas.py --archivar 857049731 857049733 ...   # desde Kobo V1
  archivo_visitas.py --listar
  archivo_visitas.py --ver "BELLA VISTA"
"""
import json, os, sqlite3, sys, unicodedata, urllib.request
from datetime import datetime

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
KOBO_V1 = "aNVGYKhswB8hFBSArTh8b8"


def token():
    for l in open(os.path.expanduser("~/.hermes/.env")):
        if l.startswith("KOBO_TOKEN="):
            return l.split("=", 1)[1].strip()
    raise SystemExit("falta KOBO_TOKEN")


def norm(s):
    import re
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def crear_tablas(con):
    con.execute("""CREATE TABLE IF NOT EXISTS auditorias_archivo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        predio_id INTEGER NOT NULL,
        fecha TEXT, concepto TEXT,
        f_cumplidos INTEGER, f_total INTEGER, f_pct REAL,
        my_cumplidos INTEGER, my_total INTEGER, my_pct REAL,
        mn_cumplidos INTEGER, mn_total INTEGER, mn_pct REAL,
        observaciones TEXT, recomendaciones TEXT, fuente TEXT,
        origen_id TEXT, archivada_en TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS respuestas_archivo (
        archivo_id INTEGER NOT NULL,
        criterio_id TEXT NOT NULL,
        respuesta TEXT,
        PRIMARY KEY (archivo_id, criterio_id))""")
    con.commit()


def calcular(sub, tipos):
    """F/My/Mn y concepto a partir de las respuestas de la submission."""
    res = {}
    for t in ("F", "My", "Mn"):
        cum = tot = 0
        for cid, tipo in tipos.items():
            if tipo != t:
                continue
            campo = f"seccion_{cid.split('.')[0]}/c_{cid.replace('.', '_')}"
            v = (sub.get(campo) or "").strip().upper()
            if not v:
                continue
            if v == "NO_APLICA":
                v = "NA"
            if v == "NA":
                continue
            tot += 1
            cum += 1 if v == "SI" else 0
        res[t] = (cum, tot, round(100.0 * cum / tot, 2) if tot else 0.0)
    ok = res["F"][2] >= 100 and res["My"][2] >= 80 and res["Mn"][2] >= 60
    return res, ("Certificable" if ok else "Aplazado")


def archivar(ids):
    T = token()
    q = urllib.request.Request(
        f"https://kf.kobotoolbox.org/api/v2/assets/{KOBO_V1}/data/?format=json&limit=200",
        headers={"Authorization": "Token " + T, "Accept": "application/json"})
    subs = {str(s.get("_id")): s for s in json.load(urllib.request.urlopen(q, timeout=120))["results"]}
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    crear_tablas(con)
    tipos = dict(con.execute("SELECT id, tipo FROM criterios").fetchall())
    predios = {norm(r["nombre"]): r["id"] for r in con.execute("SELECT id, nombre FROM predios")}

    for sid in ids:
        sub = subs.get(str(sid))
        if not sub:
            print(f"  ✗ submission {sid}: no está en Kobo V1")
            continue
        clave = norm(sub.get("nombre_predio"))
        if clave not in predios:
            print(f"  ✗ submission {sid}: el predio {sub.get('nombre_predio')!r} no está en la BD")
            continue
        pid = predios[clave]
        ya = con.execute("SELECT id FROM auditorias_archivo WHERE origen_id=?", (str(sid),)).fetchone()
        if ya:
            print(f"  = submission {sid}: ya archivada (#{ya[0]})")
            continue
        fecha = str(sub.get("fecha") or sub.get("_submission_time"))[:10]
        res, concepto = calcular(sub, tipos)
        cur = con.execute("""INSERT INTO auditorias_archivo
            (predio_id, fecha, concepto, f_cumplidos, f_total, f_pct, my_cumplidos, my_total, my_pct,
             mn_cumplidos, mn_total, mn_pct, observaciones, recomendaciones, fuente, origen_id, archivada_en)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, fecha, concepto, *res["F"], *res["My"], *res["Mn"],
             sub.get("observaciones") or sub.get("observacion"), sub.get("recomendaciones"),
             f"Kobo V1 submission {sid}", str(sid), datetime.now().isoformat(timespec="seconds")))
        aid = cur.lastrowid
        n = 0
        for cid in tipos:
            campo = f"seccion_{cid.split('.')[0]}/c_{cid.replace('.', '_')}"
            v = (sub.get(campo) or "").strip().upper()
            if not v:
                continue
            if v == "NO_APLICA":
                v = "NA"
            con.execute("INSERT INTO respuestas_archivo (archivo_id, criterio_id, respuesta) VALUES (?,?,?)",
                        (aid, cid, "SI" if v == "SI" else v))
            n += 1
        con.commit()
        nombre = con.execute("SELECT nombre FROM predios WHERE id=?", (pid,)).fetchone()[0]
        print(f"  ✓ archivada #{aid} · {nombre} · {fecha} → {concepto} "
              f"(F {res['F'][0]}/{res['F'][1]} · My {res['My'][0]}/{res['My'][1]} · "
              f"Mn {res['Mn'][0]}/{res['Mn'][1]}) · {n} respuestas · origen {sid}")


def listar():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    crear_tablas(con)
    filas = con.execute("""SELECT a.id, p.nombre, a.fecha, a.concepto, a.f_cumplidos, a.f_total,
                                  a.my_cumplidos, a.my_total, a.mn_cumplidos, a.mn_total,
                                  a.origen_id, (SELECT COUNT(*) FROM respuestas_archivo r
                                                WHERE r.archivo_id=a.id) n
                           FROM auditorias_archivo a JOIN predios p ON p.id=a.predio_id
                           ORDER BY p.nombre, a.fecha""").fetchall()
    if not filas:
        print("  (archivo vacío)"); return
    print(f"  {len(filas)} visita(s) archivada(s) — NO se muestran en el dashboard:\n")
    for r in filas:
        print(f"  #{r['id']:<3} {r['nombre']:<24} {r['fecha']} → {r['concepto']:<13} "
              f"F {r['f_cumplidos']}/{r['f_total']} · My {r['my_cumplidos']}/{r['my_total']} · "
              f"Mn {r['mn_cumplidos']}/{r['mn_total']} · {r['n']} resp · origen {r['origen_id']}")


def ver(predio):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    crear_tablas(con)
    filas = con.execute("""SELECT a.*, p.nombre FROM auditorias_archivo a JOIN predios p ON p.id=a.predio_id
                           WHERE upper(p.nombre)=upper(?) ORDER BY a.fecha""", (predio,)).fetchall()
    if not filas:
        print(f"  {predio}: sin visitas archivadas"); return
    for r in filas:
        print(f"\n  #{r['id']} {r['nombre']} · {r['fecha']} → {r['concepto']}")
        print(f"    F {r['f_cumplidos']}/{r['f_total']} = {r['f_pct']}% · My {r['my_cumplidos']}/{r['my_total']} = {r['my_pct']}% · "
              f"Mn {r['mn_cumplidos']}/{r['mn_total']} = {r['mn_pct']}%")
        print(f"    origen: {r['fuente']} · archivada: {r['archivada_en']}")
        if r['observaciones']:
            print(f"    observaciones: {str(r['observaciones'])[:160]}")
        print("    criterios que difieren del estado actual:")
        act = con.execute("""SELECT id FROM auditorias WHERE predio_id=? ORDER BY fecha DESC,id DESC LIMIT 1""",
                          (r['predio_id'],)).fetchone()
        if act:
            bd = dict(con.execute("SELECT criterio_id,respuesta FROM respuestas WHERE auditoria_id=?",
                                  (act[0],)).fetchall())
            arc = dict(con.execute("SELECT criterio_id,respuesta FROM respuestas_archivo WHERE archivo_id=?",
                                   (r['id'],)).fetchall())
            det = [(k, arc[k], bd.get(k)) for k in sorted(arc) if (arc[k] or '').upper() != (bd.get(k) or '').upper()]
            for k, va, vb in det:
                print(f"      {k:<6} archivo={va:<10} actual={vb}")
            if not det:
                print("      (idénticas)")


if __name__ == "__main__":
    if "--archivar" in sys.argv:
        i = sys.argv.index("--archivar")
        archivar(sys.argv[i + 1:])
    elif "--ver" in sys.argv:
        ver(sys.argv[sys.argv.index("--ver") + 1])
    else:
        listar()
