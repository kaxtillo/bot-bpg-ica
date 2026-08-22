#!/usr/bin/env python3
"""
Consultas y seguimiento de auditorías BPG ICA (Res. 067449).

Uso:
  python3 consultar.py              → resumen global
  python3 consultar.py predios      → lista de predios
  python3 consultar.py detalle <P>  → detalle completo última auditoría del predio
  python3 consultar.py hallazgos    → hallazgos NO de todos los predios
  python3 consultar.py seguimiento  → criterios con NO pendientes (seguimiento)
"""
import os
import sqlite3
import sys

DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")

UMBRALES = {"F": 100.0, "My": 80.0, "Mn": 60.0}


def conectar():
    return sqlite3.connect(DB)


def resumen(con):
    print("═" * 62)
    print("  📋 AUDITORÍAS BPG ICA — RES. 067449 — RESUMEN GLOBAL")
    print("═" * 62)
    n = con.execute("SELECT COUNT(*) FROM auditorias").fetchone()[0]
    cert = con.execute("SELECT COUNT(*) FROM auditorias WHERE concepto LIKE '%Certificable%'").fetchone()[0]
    apl = con.execute("SELECT COUNT(*) FROM auditorias WHERE concepto LIKE '%Aplazado%'").fetchone()[0]
    predios = con.execute("SELECT COUNT(*) FROM predios").fetchone()[0]
    print(f"  Predios evaluados : {predios}")
    print(f"  Auditorías        : {n}  (Certificables: {cert} · Aplazadas: {apl})")
    print()
    print("  ── Detalle por auditoría ──")
    for row in con.execute(
        """SELECT a.id, p.nombre, a.fecha, a.concepto, a.f_pct, a.my_pct, a.mn_pct
           FROM auditorias a JOIN predios p ON p.id=a.predio_id ORDER BY a.fecha, a.id"""
    ):
        f_ok = "✓" if (row[4] is not None and row[4] >= UMBRALES["F"]) else "✗"
        my_ok = "✓" if (row[5] is not None and row[5] >= UMBRALES["My"]) else "✗"
        mn_ok = "✓" if (row[6] is not None and row[6] >= UMBRALES["Mn"]) else "✗"
        print(
            f"  #{row[0]} {row[1]:14s} {row[2]}  {row[3]:12s} "
            f"F {row[4]}%{f_ok} · My {row[5]}%{my_ok} · Mn {row[6]}%{mn_ok}"
        )
    print()
    print("  Umbrales: F = 100% · My ≥80% · Mn ≥60% (NA excluidos)")


def predios(con):
    print("═" * 62)
    print("  🏠 PREDIOS REGISTRADOS")
    print("═" * 62)
    for row in con.execute(
        """SELECT p.nombre, p.propietario, p.municipio, p.vereda, p.especie, p.fin_zootecnico,
                  COUNT(a.id), MAX(a.fecha)
           FROM predios p LEFT JOIN auditorias a ON a.predio_id=p.id
           GROUP BY p.id ORDER BY p.nombre"""
    ):
        print(
            f"  {row[0]:14s} | {row[1] or '-':22s} | {row[2] or '-':10s} {row[3] or '-'} | "
            f"{row[4] or '-':15s} {row[5] or '-'} | {row[6]} audit. | última: {row[7] or '-'}"
        )


def normalizar(s):
    """Quita tildes y pasa a mayúsculas para búsquedas tolerantes."""
    if not s:
        return ""
    mapa = str.maketrans("ÁÉÍÓÚÜÑáéíóúüñ", "AEIOUUNaeiouun")
    return s.translate(mapa).upper().strip()


def buscar_predio(con, nombre):
    """Busca por nombre exacto o normalizado (ignora tildes/mayúsculas)."""
    fila = con.execute("SELECT * FROM predios WHERE nombre=?", (nombre.upper(),)).fetchone()
    if fila:
        return fila
    objetivo = normalizar(nombre)
    for row in con.execute("SELECT * FROM predios"):
        if normalizar(row[1]) == objetivo:
            return row
    return None


def detalle(con, predio):
    p = buscar_predio(con, predio)
    if not p:
        print(f"❌ Predio '{predio}' no encontrado. Use: python3 consultar.py predios")
        sys.exit(1)
    cols = [d[0] for d in con.execute("SELECT * FROM predios LIMIT 1").description]
    pdata = dict(zip(cols, p))
    print("═" * 62)
    print(f"  🏠 {pdata['nombre']} — {pdata['municipio'] or ''}, {pdata['departamento'] or ''}")
    print("═" * 62)
    print(f"  Propietario : {pdata['propietario'] or '-'}  CC: {pdata['identificacion'] or '-'}")
    print(f"  Vereda      : {pdata['vereda'] or '-'}  GPS: {pdata['latitud']}, {pdata['longitud']}")
    print(f"  Especie     : {pdata['especie'] or '-'} · Fin: {pdata['fin_zootecnico'] or '-'} · "
          f"RSPP: {pdata['rspp'] or '-'} · Producción: {pdata['produccion'] or '-'} · Animales: {pdata['total_animales'] or '-'}")
    a = con.execute(
        """SELECT * FROM auditorias WHERE predio_id=? ORDER BY fecha DESC, id DESC LIMIT 1""",
        (pdata["id"],),
    ).fetchone()
    if not a:
        print("  (sin auditorías)")
        return
    acols = [d[0] for d in con.execute("SELECT * FROM auditorias LIMIT 1").description]
    adata = dict(zip(acols, a))
    print()
    print(f"  ÚLTIMA AUDITORÍA — {adata['fecha']}  →  {adata['concepto'].upper()}")
    print(f"    Fundamentales: {adata['f_cumplidos']}/{adata['f_total']} ({adata['f_pct']}%)  "
          f"umbral 100% {'✓' if adata['f_pct'] >= 100 else '✗'}")
    print(f"    Mayores      : {adata['my_cumplidos']}/{adata['my_total']} ({adata['my_pct']}%)  "
          f"umbral 80% {'✓' if adata['my_pct'] >= 80 else '✗'}")
    print(f"    Menores      : {adata['mn_cumplidos']}/{adata['mn_total']} ({adata['mn_pct']}%)  "
          f"umbral 60% {'✓' if adata['mn_pct'] >= 60 else '✗'}")
    if adata.get("observaciones"):
        print(f"\n  Observaciones: {adata['observaciones']}")
    if adata.get("recomendaciones"):
        print(f"  Recomendaciones: {adata['recomendaciones']}")
    print(f"  Fuente: {adata.get('fuente') or 'desconocida'}")
    n_nos = con.execute(
        """SELECT COUNT(*) FROM respuestas WHERE auditoria_id=? AND respuesta='NO'""", (adata["id"],)
    ).fetchone()[0]
    if n_nos:
        print(f"\n  🔴 HALLAZGOS ({n_nos} criterios en NO):")
        for row in con.execute(
            """SELECT r.criterio_id, c.nombre, c.tipo, c.articulo FROM respuestas r
               JOIN criterios c ON c.id=r.criterio_id WHERE r.auditoria_id=? AND r.respuesta='NO'
               ORDER BY r.criterio_id""",
            (adata["id"],),
        ):
            print(f"    • {row[0]} {row[1]} ({row[2]} - Art. {row[3]})")


def hallazgos(con):
    print("═" * 62)
    print("  🔴 HALLAZGOS (criterios en NO) POR PREDIO")
    print("═" * 62)
    for row in con.execute(
        """SELECT p.nombre, a.id, a.fecha, r.criterio_id, c.nombre, c.tipo, c.articulo
           FROM respuestas r
           JOIN auditorias a ON a.id=r.auditoria_id
           JOIN predios p ON p.id=a.predio_id
           JOIN criterios c ON c.id=r.criterio_id
           WHERE r.respuesta='NO' ORDER BY p.nombre, a.fecha, r.criterio_id"""
    ):
        print(f"  {row[0]:14s} | {row[2]} (#{row[1]}) | {row[3]} {row[4]} ({row[5]} - Art. {row[6]})")


def seguimiento(con):
    print("═" * 62)
    print("  🔄 SEGUIMIENTO — criterios en NO que requieren acción correctiva")
    print("═" * 62)
    rows = con.execute(
        """SELECT p.nombre, r.criterio_id, c.nombre, c.tipo, c.articulo, c.pregunta, a.fecha
           FROM respuestas r
           JOIN auditorias a ON a.id=r.auditoria_id
           JOIN predios p ON p.id=a.predio_id
           JOIN criterios c ON c.id=r.criterio_id
           WHERE r.respuesta='NO'
           ORDER BY c.seccion, r.criterio_id"""
    ).fetchall()
    if not rows:
        print("  ✅ No hay hallazgos pendientes.")
        return
    for r in rows:
        print(f"  • {r[0]} — {r[1]} {r[2]} ({r[3]} - Art. {r[4]}) [{r[6]}]")
        print(f"      {r[5]}")


def main():
    con = conectar()
    args = sys.argv[1:]
    if not args or args[0] in ("resumen", "global"):
        resumen(con)
    elif args[0] == "predios":
        predios(con)
    elif args[0] == "detalle" and len(args) > 1:
        detalle(con, args[1])
    elif args[0] == "hallazgos":
        hallazgos(con)
    elif args[0] == "seguimiento":
        seguimiento(con)
    else:
        print(__doc__)
    con.close()


if __name__ == "__main__":
    main()
