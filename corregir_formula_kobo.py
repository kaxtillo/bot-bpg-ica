#!/usr/bin/env python3
"""
corregir_formula_kobo.py — Corrige las fórmulas de cálculo de un XLSForm en KoboToolbox.

Bug corregido: las expresiones `calculate` usaban referencias SIN `${}` (`int(c_1_1='si')`).
En XPath eso compara el TEXTO LITERAL "c_1_1" con 'si' → siempre falso → todos los conteos
en 0 (y `x != 'no_aplica'` siempre verdadero → el total no excluía los NA). La forma correcta
es `${c_1_1}` (pyxform la expande a la ruta absoluta del nodo).

Uso:
  python3 corregir_formula_kobo.py --uid <uid> [--ver] [--desplegar]
"""
import json, os, re, sys, urllib.error, urllib.request

KOBO = "https://kf.kobotoolbox.org/api/v2"
CAMPOS_EXPR = ("calculation", "relevant", "constraint", "choice_filter")


def token():
    for l in open(os.path.expanduser("~/.hermes/.env")):
        if l.startswith("KOBO_TOKEN="):
            return l.split("=", 1)[1].strip()
    return ""


def req(metodo, ruta, tok, cuerpo=None):
    r = urllib.request.Request(KOBO + ruta, method=metodo,
                              headers={"Authorization": "Token " + tok,
                                       "Content-Type": "application/json",
                                       "Accept": "application/json"})
    data = json.dumps(cuerpo).encode() if cuerpo is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=90) as x:
            cuerpo_txt = x.read().decode()
            return x.status, (json.loads(cuerpo_txt) if cuerpo_txt.strip() else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:800]


def texto(v):
    """El label/hint puede venir como lista ['texto', None] (multiidioma)."""
    if isinstance(v, list):
        return v[0] if v and isinstance(v[0], str) else ""
    return v if isinstance(v, str) else ""


def corregir_expresion(expr, nombres):
    """Envuelve en ${} los nombres de campo que aparecen sueltos."""
    pat = re.compile(r"(?<![\w${])([a-zA-Z_][\w]*)(?![\w}])")

    def rep(m):
        t = m.group(1)
        return "${%s}" % t if t in nombres else t
    return pat.sub(rep, expr)


def desplegar(tok, uid):
    """Asegura que la versión del borrador sea la DESPLEGADA.

    Ojo: editar el contenido crea una versión nueva pero NO la despliega.
    - POST /deployment/ solo sirve si no hay deployment previo (si no → 405).
    - PATCH /deployment/ con {"active": true} responde 200 pero NO re-despliega.
    - La forma que funciona: PATCH /deployment/ con {"version_id": <borrador>}.
    """
    st, a = req("GET", f"/assets/{uid}/?format=json", tok)
    if st != 200:
        print(f"  ❌ no se pudo leer el asset ({st})"); return False
    borrador, activa = a.get("version_id"), a.get("deployed_version_id")
    if borrador == activa:
        print(f"  ✓ ya desplegada ({activa})"); return True
    print(f"  borrador={borrador} · activa={activa}")
    stp, resp = req("POST", f"/assets/{uid}/deployment/", tok,
                    {"active": True, "backend": "openrosa"})
    if stp in (200, 201):
        print(f"  POST /deployment/ → {stp}")
    else:
        print(f"  POST /deployment/ → {stp} ({str(resp)[:70]}) → usando PATCH con version_id")
        stp, resp = req("PATCH", f"/assets/{uid}/deployment/", tok, {"version_id": borrador})
        print(f"  PATCH /deployment/ {{version_id}} → {stp}")
    st, a2 = req("GET", f"/assets/{uid}/?format=json", tok)
    ok = (a2.get("deployed_version_id") == a2.get("version_id"))
    print(f"  desplegada ahora: {a2.get('deployed_version_id')} {'✓' if ok else '✗'}")
    return ok


def main():
    args = sys.argv[1:]
    uid = args[args.index("--uid") + 1] if "--uid" in args else "a78ZWXkFgDUNVrDPtc44dG"
    tok = token()
    if not tok:
        print("❌ Falta KOBO_TOKEN"); return

    st, asset = req("GET", f"/assets/{uid}/?format=json", tok)
    if st != 200:
        print(f"❌ GET asset → {st}"); return
    print(f"Formulario: {asset.get('name')!r} · estado={asset.get('deployment_status')}")

    content = asset["content"]
    survey = content.get("survey", [])
    nombres = {r.get("name") for r in survey if r.get("name")}
    # nombres de nivel superior (los que usan otras fórmulas): f_si, concepto, total_animales…
    for r in survey:
        xp = r.get("$xpath") or ""
        if "/" not in xp and r.get("name"):
            nombres.add(r["name"])

    respaldo = f"/tmp/kobo_{uid}_asset_original.json"
    copia_original = json.loads(json.dumps(asset))   # copia ANTES de mutar
    cambios = []
    for fila in survey:
        for campo in CAMPOS_EXPR:
            if campo not in fila:
                continue
            original = fila[campo]
            if isinstance(original, list):
                nuevo = [corregir_expresion(v, nombres) if isinstance(v, str) else v for v in original]
            elif isinstance(original, str):
                nuevo = corregir_expresion(original, nombres)
            else:
                continue
            if nuevo != original:
                cambios.append((fila.get("name") or fila.get("type"), campo, original, nuevo))
                fila[campo] = nuevo

    if not cambios:
        print("✓ Sin cambios: las expresiones ya usan ${}")
        if "--desplegar" in args:
            print("\n=== asegurar despliegue ===")
            desplegar(tok, uid)
        return
    print(f"\n=== {len(cambios)} expresión(es) corregida(s) ===")
    for name, campo, antes, despues in cambios[:6]:
        print(f"\n[{name}.{campo}]")
        print(f"  ANTES:  {str(antes)[:150]}")
        print(f"  DESPUÉS:{str(despues)[:150]}")
    if len(cambios) > 6:
        print(f"\n… y {len(cambios)-6} más")

    # guardar copia de seguridad y el contenido corregido
    destino = f"/tmp/kobo_{uid}_content_corregido.json"
    json.dump(copia_original, open(respaldo, "w"), ensure_ascii=False)
    json.dump(content, open(destino, "w"), ensure_ascii=False)
    print(f"\n✓ copia original en {respaldo}")
    print(f"✓ contenido corregido en {destino}")

    if "--ver" in args:
        return

    print("\n=== PATCH del contenido (crea borrador) ===")
    st, resp = req("PATCH", f"/assets/{uid}/", tok, {"content": content})
    print(f"PATCH /assets/{uid}/ → HTTP {st}")
    if st != 200:
        print("respuesta:", resp if isinstance(resp, str) else json.dumps(resp)[:600])
        print("\n⚠️  La API rechazó el PATCH de contenido para este asset.")
        print("   Alternativa: re-subir el XLSX corregido en la UI (⋯ → Reemplazar formulario).")
        return

    print("\n=== verificar el borrador ===")
    st2, a2 = req("GET", f"/assets/{uid}/?format=json", tok)
    if st2 == 200:
        for r in a2["content"]["survey"]:
            if r.get("name") == "f_si":
                ok = "${c_1_1}" in (r.get("calculation") or "")
                print(f"  f_si ahora: {str(r.get('calculation'))[:90]}…")
                print(f"  {'✓ referencias con ${{}}' if ok else '✗ sigue sin ${{}}'}")

    if "--desplegar" in args:
        print("\n=== desplegar ===")
        desplegar(tok, uid)


if __name__ == "__main__":
    main()
