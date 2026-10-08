#!/usr/bin/env python3
"""verificar_kobo.py — Verifica que un formulario Kobo quedó corregido y desplegado.

1) Comprueba que el formulario ACTIVO es el que tiene las referencias ${} corregidas
   (deployed_version_id == version_id y el XForm compilado resuelve rutas absolutas).
2) Simula las fórmulas corregidas sobre TODAS las submissions reales y compara el
   resultado con lo que dice la base de datos (deben coincidir = fórmula correcta).

Uso: verificar_kobo.py --uid <uid> [--db auditorias_bpg.db]
"""
import json, os, re, sqlite3, sys, unicodedata
import urllib.request, urllib.error

BASE = "https://kf.kobotoolbox.org/api/v2"


def token():
    ruta = os.path.expanduser("~/.hermes/.env")
    for linea in open(ruta):
        if linea.startswith("KOBO_TOKEN="):
            return linea.split("=", 1)[1].strip()
    return ""


def pedir(tok, ruta, accept="application/json"):
    url = BASE + ruta
    q = urllib.request.Request(url, headers={"Authorization": "Token " + tok, "Accept": accept})
    try:
        with urllib.request.urlopen(q, timeout=120) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def json_de(tok, ruta):
    st, txt = pedir(tok, ruta)
    return (st, json.loads(txt)) if st == 200 and txt.strip().startswith(("{", "[")) else (st, None)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9 ]", " ", s.upper()).strip()


# ---------- 1) el formulario activo ----------
def verificar_despliegue(tok, uid):
    st, a = json_de(tok, f"/assets/{uid}/?format=json")
    if st != 200:
        print(f"  ❌ GET asset → {st}"); return None
    print(f"  formulario: {a.get('name')!r} · estado: {a.get('deployment_status')}")
    print(f"  borrador: {a.get('version_id')} · desplegada: {a.get('deployed_version_id')}")
    ok = a.get("version_id") == a.get("deployed_version_id")
    print(f"  {'✓ el ACTIVO es el corregido' if ok else '✗ el fix NO está desplegado'}")
    calc = [r for r in a["content"]["survey"] if r.get("type") == "calculate"]
    rotos = [r["name"] for r in calc if r.get("calculation") and "${" not in r["calculation"]]
    print(f"  campos calculate: {len(calc)} · sin ${{}}: {rotos or 'ninguno ✓'}")
    st, xml = pedir(tok, f"/assets/{uid}/?format=xml", accept="application/xml")
    if st == 200:
        malos = re.findall(r"int\(\s*(c_\d+_\d+)", xml)
        nodos = sorted(set(re.findall(r"(seccion_\d+/c_\d+_\d+)", xml)))
        print(f"  XForm activo: {len(xml)} chars · patrones rotos: {len(malos)} "
              f"{'✓' if not malos else malos[:3]} · nodos de criterio: {len(nodos)}")
        m = re.search(r'<bind[^>]*nodeset="[^"]*\bf_pct"[^>]*calculate="([^"]*)"', xml)
        if m:
            print(f"  f_pct en el XForm: {m.group(1)[:120].replace('&gt;','>')}")
    else:
        print(f"  ⚠️ no se pudo bajar el XForm (HTTP {st})")
    return a


# ---------- 2) simular las fórmulas sobre las submissions ----------
def evaluar(expr, valores, calculados):
    """Traduce la expresión XLSForm (XPath) a Python y la evalúa."""
    def val(nombre):
        if nombre in calculados:
            return calculados[nombre]          # las derivadas salen de lo ya calculado
        for k, v in valores.items():
            if k == nombre or k.endswith("/" + nombre):
                if v is None: return None
                s = str(v).strip()
                if s == "": return None
                try:
                    return float(s) if "." in s else int(s)
                except ValueError:
                    return s.lower() if s.isalpha() else s   # 'SI'/'Si' → 'si' (la BD guarda mayúsculas)
        return None

    e = re.sub(r"\$\{(\w+)\}", lambda m: repr(val(m.group(1))), expr)
    e = re.sub(r"\bdiv\b", "/", e)
    e = re.sub(r"\band\b", " and ", e)
    e = re.sub(r"\bor\b", " or ", e)
    e = re.sub(r"\bif\(", "_if(", e)
    e = re.sub(r"(?<![!<>=])=(?!=)", "==", e)      # '=' de XPath → '=='
    _if = lambda c, a, b: a if c else b
    return eval(e, {"_if": _if, "int": lambda x: 1 if x else 0, "round": round, "__builtins__": {}})


def calificar(survey, submission):
    exprs = {r["name"]: r.get("calculation") for r in survey if r.get("type") == "calculate"}
    orden = [n for n in ("f_si","f_total","f_pct","my_si","my_total","my_pct",
                         "mn_si","mn_total","mn_pct","concepto") if n in exprs]
    calc = {}
    for n in orden:
        try:
            calc[n] = evaluar(exprs[n], submission, calc)
        except Exception as e:
            calc[n] = f"ERROR {e}"
    return calc


def main():
    args = sys.argv[1:]
    uid = args[args.index("--uid") + 1] if "--uid" in args else "a78ZWXkFgDUNVrDPtc44dG"
    db = args[args.index("--db") + 1] if "--db" in args else "auditorias_bpg.db"
    tok = token()
    if not tok:
        print("❌ falta KOBO_TOKEN"); return

    print("=== 1) formulario activo ===")
    asset = verificar_despliegue(tok, uid)
    if not asset:
        return
    survey = asset["content"]["survey"]

    print("\n=== 2) simulación de las fórmulas corregidas vs la base de datos ===")
    st, data = json_de(tok, f"/assets/{uid}/data/?format=json&limit=200")
    if st != 200 or not data:
        print(f"  ⚠️ no se pudieron leer las submissions ({st})"); return
    subs = data.get("results", [])
    print(f"  submissions: {len(subs)}")

    con = sqlite3.connect(db)
    predios = {norm(n): (pid, n) for pid, n in con.execute("SELECT id, nombre FROM predios")}

    ok = dif = sin = 0
    for s in subs:
        # identificar el predio por cualquier valor que coincida con un nombre de la BD
        nombre_bd = None
        for k, v in s.items():
            if isinstance(v, str) and norm(v) in predios:
                nombre_bd = predios[norm(v)][1]
                break
        calc = calificar(survey, s)
        if not nombre_bd:
            sin += 1
            print(f"  ? submission {str(s.get('_id'))[:8]} → no identifico el predio "
                  f"(calculado: F {calc.get('f_pct')}% My {calc.get('my_pct')}% Mn {calc.get('mn_pct')}% → {calc.get('concepto')})")
            continue
        fila = con.execute("""SELECT a.f_cumplidos,a.f_total,a.f_pct,a.my_cumplidos,a.my_total,
                                     a.mn_cumplidos,a.mn_total,a.concepto
                              FROM auditorias a WHERE a.predio_id=?
                              ORDER BY a.fecha DESC LIMIT 1""", (predios[norm(nombre_bd)][0],)).fetchone()
        if not fila:
            sin += 1; print(f"  ? {nombre_bd}: sin auditoría en la BD"); continue
        coincide = (calc.get("f_cumplidos", calc.get("f_si")) == fila[0] and
                    calc.get("f_total") == fila[1] and
                    calc.get("my_si") == fila[3] and calc.get("my_total") == fila[4] and
                    calc.get("mn_si") == fila[5] and calc.get("mn_total") == fila[6] and
                    calc.get("concepto") == fila[7])
        if coincide:
            ok += 1
            print(f"  ✓ {nombre_bd:<22} F {calc['f_si']}/{calc['f_total']}={calc['f_pct']}% "
                  f"My {calc['my_si']}/{calc['my_total']}={calc['my_pct']}% "
                  f"Mn {calc['mn_si']}/{calc['mn_total']}={calc['mn_pct']}% → {calc['concepto']}")
        else:
            dif += 1
            print(f"  ✗ {nombre_bd:<22} (submission {str(s.get('_submission_time'))[:10]}) formulario: "
                  f"F {calc.get('f_si')}/{calc.get('f_total')} "
                  f"My {calc.get('my_si')}/{calc.get('my_total')} Mn {calc.get('mn_si')}/{calc.get('mn_total')} "
                  f"→ {calc.get('concepto')}   ||   BD: F {fila[0]}/{fila[1]} My {fila[3]}/{fila[4]} "
                  f"Mn {fila[5]}/{fila[6]} → {fila[7]}")
    print(f"\n  RESULTADO: {ok} coinciden · {dif} difieren · {sin} sin comparar")
    con.close()


if __name__ == "__main__":
    main()
