#!/usr/bin/env python3
"""revisar_duplicados_kobo.py — Busca submissions duplicadas en un formulario Kobo.

Compara las submissions entre sí (por predio) y contra la base de datos, para detectar
auditorías repetidas del mismo predio con respuestas distintas (que hacen que el
formulario y el dashboard no coincidan).
"""
import json, os, re, sqlite3, sys, unicodedata
import urllib.request

UID = sys.argv[sys.argv.index("--uid") + 1] if "--uid" in sys.argv else "aNVGYKhswB8hFBSArTh8b8"
DB = "auditorias_bpg.db"


def token():
    for l in open(os.path.expanduser("~/.hermes/.env")):
        if l.startswith("KOBO_TOKEN="):
            return l.split("=", 1)[1].strip()
    return ""


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9 ]", " ", s.upper()).strip()


T = token()
q = urllib.request.Request(
    f"https://kf.kobotoolbox.org/api/v2/assets/{UID}/data/?format=json&limit=500",
    headers={"Authorization": "Token " + T, "Accept": "application/json"})
subs = json.load(urllib.request.urlopen(q, timeout=180))["results"]
con = sqlite3.connect(DB)
predios = {norm(n): n for _, n in con.execute("SELECT id, nombre FROM predios")}

porpredio = {}
for s in subs:
    hallado = None
    for v in s.values():
        if isinstance(v, str) and norm(v) in predios:
            hallado = predios[norm(v)]
            break
    porpredio.setdefault(hallado or f"(sin identificar, id={s.get('_id')})", []).append(s)

print(f"submissions: {len(subs)} · predios distintos: {len(porpredio)}\n")
print("=== predios con MÁS DE UNA submission ===")
dups = 0
for nombre, lst in sorted(porpredio.items()):
    if len(lst) < 2:
        continue
    dups += 1
    ids = [str(x.get("_id")) for x in lst]
    fechas = [str(x.get("_submission_time"))[:16] for x in lst]
    claves = set()
    for s in lst:
        for k in s:
            if k.startswith("seccion_"):
                claves.add(k)
    difs = []
    for k in sorted(claves):
        vals = [s.get(k) for s in lst]
        if len({str(v) for v in vals}) > 1:
            difs.append((k.split("/")[-1], [str(v) for v in vals]))
    print(f"\n  {nombre}  ·  {len(lst)} submissions")
    print(f"    ids: {ids}")
    print(f"    fechas: {fechas}")
    if difs:
        print(f"    criterios con respuestas DISTINTAS: {len(difs)}")
        for c, vs in difs[:8]:
            print(f"      {c:<8} {vs}")
    else:
        print("    ✓ respuestas idénticas (duplicado exacto)")
print(f"\n-> {dups} predio(s) con submissions duplicadas")
