#!/usr/bin/env python3
"""
revisar_duplicados_predios.py — Detecta predios repetidos o confundibles en la BD.

Busca por seis criterios independientes:
  A) mismo nombre base (ignorando EL/LA/LOS/LAS y tildes)
  B) nombres muy parecidos (similitud de texto ≥ umbral)
  C) mismo propietario
  D) misma identificación
  E) coordenadas a menos de N metros (posible mismo predio)
  F) veredas o municipios con grafías distintas para el mismo lugar

No borra nada: solo reporta. La corrección de datos maestros se hace en la hoja de
Google (que es la fuente) y las visitas duplicadas con `archivo_visitas.py`.

Uso:
    revisar_duplicados_predios.py [--metros 100] [--similitud 0.75]
"""
import argparse, difflib, math, os, re, sqlite3, sys, unicodedata
from itertools import combinations

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")
ART = {"el", "la", "los", "las", "de", "del", "predio", "finca", "parcela"}


def sin_tildes(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def plano(s):
    return re.sub(r"[^a-z0-9]", "", sin_tildes(s))


def base(nombre):
    t = [p for p in re.split(r"[\s\-_.,]+", sin_tildes(nombre)) if p]
    while t and t[0] in ART:
        t.pop(0)
    return "".join(p for p in t if p not in ART)


def distancia(a, b):
    if None in (a["latitud"], a["longitud"], b["latitud"], b["longitud"]):
        return None
    dx = (a["latitud"] - b["latitud"]) * 111320
    dy = (a["longitud"] - b["longitud"]) * 111320 * math.cos(math.radians(a["latitud"]))
    return math.hypot(dx, dy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metros", type=float, default=100)
    ap.add_argument("--similitud", type=float, default=0.75)
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    filas = con.execute("""
        SELECT p.id, p.nombre, p.propietario, p.identificacion, p.municipio, p.vereda,
               p.latitud, p.longitud,
               (SELECT COUNT(*) FROM auditorias WHERE predio_id=p.id) n_aud,
               (SELECT MAX(fecha) FROM auditorias WHERE predio_id=p.id) ultima,
               (SELECT concepto FROM auditorias WHERE predio_id=p.id ORDER BY fecha DESC, id DESC LIMIT 1) concepto
        FROM predios p ORDER BY p.nombre""").fetchall()

    print(f"Predios revisados: {len(filas)}")
    hallazgos = 0

    grupos = {}
    for f in filas:
        grupos.setdefault(base(f["nombre"]), []).append(f)
    print("\nA) Mismo nombre base (EL RAMAL vs RAMAL)")
    for k, g in sorted(grupos.items()):
        if len(g) > 1:
            hallazgos += 1
            print(f"   '{k}' → {len(g)} predios")
            for f in g:
                print(f"     id={f['id']:<5} {f['nombre']:<22} {str(f['propietario'])[:26]:<26} "
                      f"{f['municipio']}/{f['vereda']:<16} {f['n_aud']} aud · {f['concepto']}")
    if not any(len(g) > 1 for g in grupos.values()):
        print("   sin coincidencias")

    print(f"\nB) Nombres parecidos (similitud ≥ {a.similitud})")
    hallado = False
    for x, y in combinations(filas, 2):
        if base(x["nombre"]) == base(y["nombre"]):
            continue
        r = difflib.SequenceMatcher(None, plano(x["nombre"]), plano(y["nombre"])).ratio()
        if r >= a.similitud:
            hallado = True
            hallazgos += 1
            print(f"   {r:.2f} · {x['nombre']} (id {x['id']}, {x['propietario']}) ↔ "
                  f"{y['nombre']} (id {y['id']}, {y['propietario']})")
    if not hallado:
        print("   sin coincidencias")

    for etiqueta, campo, titulo in (
            ("C", "propietario", "C) Mismo propietario"),
            ("D", "identificacion", "D) Misma identificación")):
        print("\n" + titulo)
        idx = {}
        for f in filas:
            k = plano(f[campo])
            if k:
                idx.setdefault(k, []).append(f)
        dup = {k: v for k, v in idx.items() if len(v) > 1}
        if not dup:
            print("   sin coincidencias")
        for k, g in dup.items():
            hallazgos += 1
            print(f"   {g[0][campo]}: " + ", ".join(f"{x['nombre']} (id {x['id']})" for x in g))

    print(f"\nE) Coordenadas a menos de {a.metros:.0f} m")
    hallado = False
    for x, y in combinations(filas, 2):
        d = distancia(x, y)
        if d is not None and d < a.metros:
            hallado = True
            hallazgos += 1
            print(f"   {d:4.0f} m · {x['nombre']} (id {x['id']}, {x['propietario'][:20] if x['propietario'] else '-'}) ↔ "
                  f"{y['nombre']} (id {y['id']}, {y['propietario'][:20] if y['propietario'] else '-'})")
    if not hallado:
        print("   sin coincidencias")

    print("\nF) Veredas y municipios con grafías equivalentes")
    sys.path.insert(0, BASE)
    try:
        from importar_hoja import canon_vereda, canon_municipio
    except Exception:
        canon_vereda = canon_municipio = lambda v: v
    for campo, canon, etiqueta in (("vereda", canon_vereda, "vereda"), ("municipio", canon_municipio, "municipio")):
        valores = {}
        for f in filas:
            if f[campo]:
                valores.setdefault(plano(f[campo]), set()).add(f[campo])
        malos = {k: v for k, v in valores.items() if len(v) > 1}
        for k, v in malos.items():
            hallazgos += 1
            print(f"   {etiqueta}: {sorted(v)} → se unifican como {canon(sorted(v)[0])!r}")
        sin_canon = {f[campo] for f in filas if f[campo] and canon(f[campo]) != f[campo]}
        for v in sorted(sin_canon):
            print(f"   {etiqueta} {v!r} no está en la lista canónica (se guarda tal cual) → {canon(v)!r}")

    print(f"\nTotal de hallazgos: {hallazgos}")
    print("Recuerda: los datos maestros se corrigen en la HOJA de Google, no en la BD "
          "(la hoja sobreescribe en cada sincronización).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
