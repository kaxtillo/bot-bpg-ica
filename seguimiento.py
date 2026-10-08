#!/usr/bin/env python3
"""
seguimiento.py — Seguimiento de hallazgos BPG (Res. 067449).

Crea/mantiene la tabla `seguimiento` en la BD: una fila por hallazgo (criterio
respondido NO) de la auditoría más reciente de cada predio, con estado
(pendiente / en_proceso / cerrado), responsable, plazo y evidencia.

Uso:
  python3 seguimiento.py sync [--predio X]   # crear/actualizar filas desde las auditorías
  python3 seguimiento.py listar [--predio X] [--estado E] [--abiertos]
  python3 seguimiento.py resumen             # avance por predio
  python3 seguimiento.py marcar <predio> <criterio> <estado> [--notas "..."] [--evidencia "..."]
  python3 seguimiento.py historial <predio> <criterio>

Estados: pendiente | en_proceso | cerrado
"""
import os, sqlite3, sys
from datetime import date, datetime, timedelta

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
ESTADOS = ("pendiente", "en_proceso", "cerrado")

sys.path.insert(0, BASE)
from generar_plan_accion import ACCIONES, GENERICA, UMBRALES  # noqa: E402

ESQUEMA = """
CREATE TABLE IF NOT EXISTS seguimiento (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    auditoria_id     INTEGER NOT NULL REFERENCES auditorias(id),
    predio_id        INTEGER NOT NULL REFERENCES predios(id),
    criterio_id      TEXT    NOT NULL REFERENCES criterios(id),
    estado           TEXT    NOT NULL DEFAULT 'pendiente'
                     CHECK (estado IN ('pendiente','en_proceso','cerrado')),
    obligatorio      INTEGER NOT NULL DEFAULT 0,
    responsable      TEXT,
    plazo_dias       INTEGER,
    fecha_limite     TEXT,
    evidencia        TEXT,
    notas            TEXT,
    creado_en        TEXT,
    actualizado_en   TEXT,
    cerrado_en       TEXT,
    UNIQUE (auditoria_id, criterio_id)
);
CREATE INDEX IF NOT EXISTS idx_seg_predio ON seguimiento(predio_id);
CREATE INDEX IF NOT EXISTS idx_seg_estado ON seguimiento(estado);
"""


def conectar():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con


def buscar_predio(con, nombre):
    return con.execute("SELECT * FROM predios WHERE UPPER(TRIM(nombre))=?",
                       (nombre.strip().upper(),)).fetchone()


def auditoria_reciente(con, predio_id):
    return con.execute(
        "SELECT * FROM auditorias WHERE predio_id=? ORDER BY fecha DESC, id DESC LIMIT 1",
        (predio_id,)).fetchone()


def ruta_obligatoria(con, a, hallazgos):
    """Ids de criterios cuya resolución es OBLIGATORIA para certificar:
    todos los F en NO + los Mn necesarios para superar el umbral.
    (Si My ya cumple el umbral, sus hallazgos son recomendados.)"""
    f_no = [h["id"] for h in hallazgos if h["tipo"] == "F"]
    mn_no = [h for h in hallazgos if h["tipo"] == "Mn"]
    total_mn = a["mn_total"] or 0
    cum_mn = a["mn_cumplidos"] or 0
    import math
    necesarios = max(0, math.ceil(UMBRALES["Mn"] / 100 * total_mn - cum_mn))
    oblig = set(f_no) | {h["id"] for h in mn_no[:necesarios]}
    if not (a["my_pct"] or 0) >= UMBRALES["My"]:
        my_no = [h for h in hallazgos if h["tipo"] == "My"]
        import math as _m
        faltan = max(0, _m.ceil(UMBRALES["My"] / 100 * (a["my_total"] or 0) - (a["my_cumplidos"] or 0)))
        oblig |= {h["id"] for h in my_no[:faltan]}
    return oblig


def hallazgos_de(con, auditoria_id):
    hs = con.execute(
        """SELECT c.id, c.tipo, c.nombre FROM respuestas r
           JOIN criterios c ON c.id=r.criterio_id
           WHERE r.auditoria_id=? AND r.respuesta='NO'""", (auditoria_id,)).fetchall()
    orden = {"F": 1, "My": 2, "Mn": 3}
    return sorted(hs, key=lambda h: (orden.get(h["tipo"], 9), [int(x) for x in h["id"].split(".")]))


def sync(con, predio=None):
    if predio:
        p = buscar_predio(con, predio)
        if not p:
            print(f"❌ Predio no encontrado: {predio}"); return
        predios = [p]
    else:
        predios = con.execute(
            """SELECT p.* FROM predios p WHERE EXISTS
               (SELECT 1 FROM auditorias a WHERE a.predio_id=p.id) ORDER BY p.nombre""").fetchall()
    ahora = datetime.now().isoformat(timespec="seconds")
    creados = actualizados = 0
    for p in predios:
        a = auditoria_reciente(con, p["id"])
        if not a:
            continue
        hs = hallazgos_de(con, a["id"])
        oblig = ruta_obligatoria(con, a, hs)
        for h in hs:
            accion, resp, plazo, evid = ACCIONES.get(h["id"], GENERICA)
            existe = con.execute(
                "SELECT id FROM seguimiento WHERE auditoria_id=? AND criterio_id=?",
                (a["id"], h["id"])).fetchone()
            if existe:
                # refrescar metadatos sin tocar estado/notas del usuario
                con.execute(
                    """UPDATE seguimiento SET obligatorio=?, responsable=?, plazo_dias=?,
                       fecha_limite=COALESCE(fecha_limite,?), evidencia=?, actualizado_en=?
                       WHERE id=?""",
                    (1 if h["id"] in oblig else 0, resp, plazo,
                     (date.today() + timedelta(days=plazo)).isoformat(), evid, ahora, existe["id"]))
                actualizados += 1
            else:
                con.execute(
                    """INSERT INTO seguimiento (auditoria_id,predio_id,criterio_id,estado,
                       obligatorio,responsable,plazo_dias,fecha_limite,evidencia,creado_en,actualizado_en)
                       VALUES (?,?,?,'pendiente',?,?,?,?,?,?,?)""",
                    (a["id"], p["id"], h["id"], 1 if h["id"] in oblig else 0, resp, plazo,
                     (date.today() + timedelta(days=plazo)).isoformat(), evid, ahora, ahora))
                creados += 1
    con.commit()
    print(f"✅ sync: {creados} hallazgo(s) nuevos · {actualizados} actualizados")


def listar(con, predio=None, estado=None, abiertos=False):
    q = """SELECT s.*, p.nombre predio, c.tipo, c.nombre criterio FROM seguimiento s
           JOIN predios p ON p.id=s.predio_id JOIN criterios c ON c.id=s.criterio_id WHERE 1=1"""
    args = []
    if predio:
        p = buscar_predio(con, predio)
        if not p:
            print(f"❌ Predio no encontrado: {predio}"); return
        q += " AND s.predio_id=?"; args.append(p["id"])
    if estado:
        q += " AND s.estado=?"; args.append(estado)
    if abiertos:
        q += " AND s.estado!='cerrado'"
    q += " ORDER BY p.nombre, CASE c.tipo WHEN 'F' THEN 1 WHEN 'My' THEN 2 ELSE 3 END, s.criterio_id"
    filas = con.execute(q, args).fetchall()
    if not filas:
        print("(sin resultados)"); return
    print(f"{'PREDIO':<24}{'CRIT':<7}{'TIPO':<4}{'ESTADO':<11}{'OBL':<5}{'LÍMITE':<12}NOTAS")
    for f in filas:
        print(f"{f['predio'][:23]:<24}{f['criterio_id']:<7}{f['tipo']:<4}{f['estado']:<11}"
              f"{'SÍ' if f['obligatorio'] else '-':<5}{f['fecha_limite'] or '':<12}{(f['notas'] or '')[:30]}")
    print(f"\n{len(filas)} fila(s)")


def resumen(con):
    filas = con.execute(
        """SELECT p.nombre predio,
                  COUNT(*) total,
                  SUM(s.estado='pendiente') pend,
                  SUM(s.estado='en_proceso') proc,
                  SUM(s.estado='cerrado') cerr,
                  SUM(s.obligatorio=1) oblig,
                  SUM(s.obligatorio=1 AND s.estado='cerrado') oblig_cerr
           FROM seguimiento s JOIN predios p ON p.id=s.predio_id
           GROUP BY p.id ORDER BY p.nombre""").fetchall()
    if not filas:
        print("(sin seguimiento — ejecuta: seguimiento.py sync)"); return
    print(f"{'PREDIO':<26}{'TOTAL':<7}{'PEND':<6}{'PROC':<6}{'CERR':<6}{'AVANCE':<9}OBLIGATORIOS")
    for f in filas:
        av = f"{100*f['cerr']//f['total']}%" if f["total"] else "—"
        ob = f"{f['oblig_cerr']}/{f['oblig']}"
        print(f"{f['predio'][:25]:<26}{f['total']:<7}{f['pend']:<6}{f['proc']:<6}{f['cerr']:<6}{av:<9}{ob}")
    t = con.execute("""SELECT COUNT(*) total, SUM(estado='cerrado') cerr,
                       SUM(obligatorio=1) ob, SUM(obligatorio=1 AND estado='cerrado') obc
                       FROM seguimiento""").fetchone()
    print(f"\nTOTAL: {t['total']} hallazgo(s) — {t['cerr']} cerrados "
          f"({100*(t['cerr'] or 0)//max(1,t['total'])}%) · obligatorios {t['obc']}/{t['ob']}")


def marcar(con, predio, criterio, estado, notas=None, evidencia=None):
    if estado not in ESTADOS:
        print(f"❌ Estado inválido. Usa: {', '.join(ESTADOS)}"); return
    p = buscar_predio(con, predio)
    if not p:
        print(f"❌ Predio no encontrado: {predio}"); return
    a = auditoria_reciente(con, p["id"])
    row = con.execute("SELECT * FROM seguimiento WHERE predio_id=? AND criterio_id=?",
                      (p["id"], criterio)).fetchone()
    if not row:
        print(f"❌ No hay fila de seguimiento para {p['nombre']} / criterio {criterio}. "
              f"Ejecuta: seguimiento.py sync --predio \"{p['nombre']}\""); return
    ahora = datetime.now().isoformat(timespec="seconds")
    con.execute(
        """UPDATE seguimiento SET estado=?, notas=COALESCE(?,notas),
           evidencia=COALESCE(?,evidencia), actualizado_en=?,
           cerrado_en=CASE WHEN ?='cerrado' THEN ? ELSE NULL END WHERE id=?""",
        (estado, notas, evidencia, ahora, estado, ahora, row["id"]))
    con.commit()
    print(f"✅ {p['nombre']} · criterio {criterio} → {estado}")


def historial(con, predio, criterio):
    p = buscar_predio(con, predio)
    if not p:
        print(f"❌ Predio no encontrado: {predio}"); return
    r = con.execute("SELECT * FROM seguimiento WHERE predio_id=? AND criterio_id=?",
                    (p["id"], criterio)).fetchone()
    if not r:
        print("(sin fila)"); return
    for k in r.keys():
        print(f"  {k:<16} = {r[k]}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    cmd, con = args[0], conectar()
    predio = args[args.index("--predio") + 1] if "--predio" in args else None
    if cmd == "sync":
        sync(con, predio)
    elif cmd == "listar":
        estado = args[args.index("--estado") + 1] if "--estado" in args else None
        listar(con, predio, estado, "--abiertos" in args)
    elif cmd == "resumen":
        resumen(con)
    elif cmd == "marcar":
        if len(args) < 4:
            print("Uso: marcar <predio> <criterio> <estado> [--notas ...] [--evidencia ...]"); return
        notas = args[args.index("--notas") + 1] if "--notas" in args else None
        evid = args[args.index("--evidencia") + 1] if "--evidencia" in args else None
        marcar(con, args[1], args[2], args[3], notas, evid)
    elif cmd == "historial":
        historial(con, args[1], args[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
