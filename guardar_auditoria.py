#!/usr/bin/env python3
"""
Guarda una auditoría BPG ICA (Res. 067449) en la base de consolidación.
Calcula automáticamente los porcentajes (NA excluidos del denominador) y el
concepto final según la metodología de la Forma 3-852 V6.

Uso:
  python3 guardar_auditoria.py < archivo.json      (JSON por stdin)
  python3 guardar_auditoria.py /ruta/auditoria.json

Formato JSON de entrada:
{
  "predio": "EL TESORO", "propietario": "...", "identificacion": "...",
  "telefono": "...", "email": "...", "departamento": "Cauca",
  "municipio": "...", "vereda": "...", "latitud": 2.45, "longitud": -76.6,
  "rspp": "SI", "especie": "BOVINA", "fin_zootecnico": "LECHE",
  "produccion": "500", "total_animales": 50,
  "fecha": "2026-08-07",                       // opcional, hoy por defecto
  "detalle_puntos": {"1.1": "SI", "1.2": "NO", ...}   // 62 criterios
}
"""
import json
import os
import sqlite3
import sys
from datetime import date

DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")

UMBRALES = {"F": 100.0, "My": 80.0, "Mn": 60.0}
TIPOS = ("F", "My", "Mn")


def cargar_json():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            return json.load(f)
    return json.load(sys.stdin)


def calcular(detalle, con):
    """Calcula cumplidos/total/pct por tipo. NA excluido del denominador."""
    res = {}
    for t in TIPOS:
        rows = con.execute(
            "SELECT id FROM criterios WHERE tipo=?", (t,)
        ).fetchall()
        cumplidos = 0
        total = 0
        for (cid,) in rows:
            r = detalle.get(cid, "").strip().upper()
            if r == "SI":
                cumplidos += 1
                total += 1
            elif r == "NO":
                total += 1
            # NA no suma al denominador
        pct = round(cumplidos / total * 100, 2) if total else 0.0
        res[t] = {"cumplidos": cumplidos, "total": total, "pct": pct}
    return res


def veredicto(res):
    for t in TIPOS:
        if res[t]["pct"] < UMBRALES[t]:
            return "Aplazado"
    return "Certificable"


def hallazgos(detalle, con):
    nos = []
    for cid, r in detalle.items():
        if r.strip().upper() == "NO":
            fila = con.execute(
                "SELECT nombre, tipo, articulo FROM criterios WHERE id=?", (cid,)
            ).fetchone()
            if fila:
                nos.append((cid, fila[0], fila[1], fila[2]))
    return sorted(nos, key=lambda x: x[0])


def main():
    d = cargar_json()
    detalle = {k.strip(): v.strip().upper() for k, v in d.get("detalle_puntos", {}).items()}
    if len(detalle) < 62:
        faltan = 62 - len(detalle)
        print(f"⚠️  Aviso: se recibieron {len(detalle)} respuestas (faltan {faltan}). "
              "Los criterios sin responder se ignoran.", file=sys.stderr)

    con = sqlite3.connect(DB)

    # validar que existan criterios en la BD (si no, sembrar)
    if con.execute("SELECT COUNT(*) FROM criterios").fetchone()[0] < 62:
        print("La BD no tiene los 62 criterios. Ejecute primero: python3 crear_bd.py", file=sys.stderr)
        sys.exit(2)

    res = calcular(detalle, con)
    concepto = veredicto(res)
    obs = d.get("observaciones") or ""
    nos = hallazgos(detalle, con)
    if nos and not obs:
        obs = "; ".join(f"{cid}: {nombre}" for cid, nombre, _, _ in nos)

    # ── upsert predio ──
    nombre = (d.get("predio") or "").strip().upper()
    if not nombre:
        print("❌ Falta el campo 'predio'.", file=sys.stderr)
        sys.exit(2)
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
            nombre, d.get("propietario"), d.get("identificacion"), d.get("telefono"),
            d.get("email"), d.get("departamento"), d.get("municipio"), d.get("vereda"),
            d.get("latitud"), d.get("longitud"), d.get("rspp"), d.get("especie"),
            d.get("fin_zootecnico"), d.get("produccion"), d.get("total_animales"),
        ),
    )
    pid = con.execute("SELECT id FROM predios WHERE nombre=?", (nombre,)).fetchone()[0]

    fecha = d.get("fecha") or date.today().isoformat()
    # si ya existe auditoría con misma fecha y concepto → actualizar; si no → nueva
    existente = con.execute(
        "SELECT id FROM auditorias WHERE predio_id=? AND fecha=? AND concepto=?",
        (pid, fecha, concepto),
    ).fetchone()
    if existente:
        aid = existente[0]
        con.execute("DELETE FROM respuestas WHERE auditoria_id=?", (aid,))
        con.execute(
            """UPDATE auditorias SET f_cumplidos=?, f_total=?, f_pct=?, my_cumplidos=?, my_total=?,
               my_pct=?, mn_cumplidos=?, mn_total=?, mn_pct=?, observaciones=?, fuente=?
               WHERE id=?""",
            (
                res["F"]["cumplidos"], res["F"]["total"], res["F"]["pct"],
                res["My"]["cumplidos"], res["My"]["total"], res["My"]["pct"],
                res["Mn"]["cumplidos"], res["Mn"]["total"], res["Mn"]["pct"],
                obs, "bot auditoria",
                aid,
            ),
        )
        modo = "actualizada"
    else:
        cur = con.execute(
            """INSERT INTO auditorias (predio_id, fecha, concepto, f_cumplidos, f_total, f_pct,
               my_cumplidos, my_total, my_pct, mn_cumplidos, mn_total, mn_pct, observaciones, fuente)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, fecha, concepto,
                res["F"]["cumplidos"], res["F"]["total"], res["F"]["pct"],
                res["My"]["cumplidos"], res["My"]["total"], res["My"]["pct"],
                res["Mn"]["cumplidos"], res["Mn"]["total"], res["Mn"]["pct"],
                obs, "bot auditoria",
            ),
        )
        aid = cur.lastrowid
        modo = "nueva"

    for cid, r in detalle.items():
        if r in ("SI", "NO", "NA"):
            con.execute(
                "INSERT OR REPLACE INTO respuestas (auditoria_id, criterio_id, respuesta) VALUES (?,?,?)",
                (aid, cid, r),
            )
    con.commit()

    # ── reporte ──
    print("═" * 56)
    print(f"  📋 AUDITORÍA BPG ICA — {nombre} ({fecha}) [{modo}]")
    print("═" * 56)
    for t, label in (("F", "Fundamentales"), ("My", "Mayores"), ("Mn", "Menores")):
        r = res[t]
        ok = "✓" if r["pct"] >= UMBRALES[t] else "✗"
        print(f"  {label:14s}: {r['cumplidos']}/{r['total']} ({r['pct']}%)  "
              f"umbral {UMBRALES[t]}% {ok}")
    print(f"  Concepto     : {'✅ CERTIFICABLE' if concepto == 'Certificable' else '🔴 APLAZADO'}")
    if nos:
        print(f"\n  🔴 Hallazgos ({len(nos)}):")
        for cid, nom, t, art in nos:
            print(f"    • {cid} {nom} ({t} - Art. {art})")
    if obs:
        print(f"\n  Observaciones: {obs}")
    print(f"\n  💾 Guardado en {DB} (auditoría #{aid})")
    con.close()


if __name__ == "__main__":
    main()
