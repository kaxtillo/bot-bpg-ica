#!/usr/bin/env python3
"""
limpiar_secretos_repo.py — Quita del repo público las credenciales de Google.

Escanea TODO el repo (no una lista fija: la primera versión dejó 16 archivos sin
limpiar) y, en cada archivo Python con secretos incrustados, reemplaza los literales
por una lectura de ~/.hermes/google_token.json (las credenciales reales nunca van al repo).
Además borra los archivos de credenciales y refuerza el .gitignore.

Sólo sube un archivo si compila (py_compile) y su contenido cambió.
Uso: limpiar_secretos_repo.py [--ver]
"""
import base64, json, os, re, subprocess, sys, tempfile, urllib.error, urllib.request

REPO = "kaxtillo/bot-bpg-ica"
RAMA = "main"
BORRAR = ["credentials.json", "token_final.json", "oauth_state.json"]
TOKEN = [l.split("=", 1)[1].strip() for l in open(os.path.expanduser("~/.hermes/.env"))
         if l.startswith("GITHUB_TOKEN=")][0]

PATRONES = [
    (r"(['\"])(\d{12}-[a-z0-9]{20,}\.apps\.googleusercontent\.com)\1", "client_id"),
    (r"(['\"])GOCSPX-[A-Za-z0-9_\-]{10,}\1", "client_secret"),
    (r"(['\"])1//0[A-Za-z0-9_\-]{25,}\1", "refresh_token"),
    (r"(['\"])ya29\.[A-Za-z0-9_\-]{20,}\1", "access_token"),
]

AYUDA = '''

def _gcred(campo, por_defecto=""):
    """Credencial de Google leída de ~/.hermes/google_token.json (NUNCA del código).

    Los secretos no van en el repositorio: se leen en tiempo de ejecución del archivo
    de token, que vive fuera del repo y no se publica.
    """
    import json as _json, os as _os
    try:
        with open(_os.path.expanduser("~/.hermes/google_token.json")) as f:
            return _json.load(f).get(campo, por_defecto)
    except Exception:
        return por_defecto

'''


def api(metodo, ruta, cuerpo=None):
    q = urllib.request.Request("https://api.github.com" + ruta, method=metodo,
                               data=json.dumps(cuerpo).encode() if cuerpo else None,
                               headers={"Authorization": "Bearer " + TOKEN,
                                        "Accept": "application/vnd.github+json",
                                        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(q, timeout=90) as r:
            b = r.read().decode()
            return r.status, (json.loads(b) if b.strip().startswith(("{", "[")) else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:200]}


def traer(ruta):
    st, d = api("GET", f"/repos/{REPO}/contents/{ruta}?ref={RAMA}")
    if st != 200 or not isinstance(d, dict) or "content" not in d:
        return None, None
    return base64.b64decode(d["content"]).decode(errors="replace"), d["sha"]


def archivos_del_repo():
    """Todas las rutas del repo, vía el árbol de git (una sola petición)."""
    st, d = api("GET", f"/repos/{REPO}/git/trees/{RAMA}?recursive=1")
    if st != 200:
        raise SystemExit(f"no pude listar el árbol del repo (HTTP {st})")
    return [n["path"] for n in d.get("tree", []) if n.get("type") == "blob"]


def limpia(txt):
    """Reemplaza literales de credenciales por _gcred(...) y añade el helper si falta."""
    usados = []
    for patron, etiqueta in PATRONES:
        def rep(m, et=etiqueta):
            usados.append(et)
            return "_gcred('client_secret')" if et in ("client_secret", "refresh_token", "access_token") else "_gcred('client_id')"
        txt = re.sub(patron, rep, txt)
    if usados and "def _gcred(" not in txt:
        lineas = txt.split("\n")
        if lineas and lineas[0].startswith("#!"):
            txt = lineas[0] + "\n" + AYUDA + "\n".join(lineas[1:])
        else:
            txt = AYUDA.lstrip("\n") + txt
    return txt, usados


def compila(codigo):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(codigo)
        ruta = f.name
    r = subprocess.run([sys.executable, "-m", "py_compile", ruta], capture_output=True, text=True)
    os.unlink(ruta)
    return r.returncode == 0, r.stderr[-300:]


def main():
    ver = "--ver" in sys.argv
    print(f"Limpieza de credenciales en {REPO} ({'SIMULACIÓN' if ver else 'REAL'})\n")
    rutas = archivos_del_repo()
    pys = [p for p in rutas if p.endswith(".py")]
    print(f"archivos en el repo: {len(rutas)} ({len(pys)} .py)\n")

    print("── 1) archivos con secretos incrustados ──")
    limpiados = sin_cambio = omitidos = 0
    otros = []
    for ruta in pys:
        txt, sha = traer(ruta)
        if txt is None:
            continue
        if not any(re.search(p, txt) for p, _ in PATRONES):
            continue
        nuevo, usados = limpia(txt)
        ok, err = compila(nuevo)
        if not ok:
            omitidos += 1
            print(f"  ✗ {ruta}: no compila tras limpiar ({err.strip()[:70]}) — se omite")
            continue
        print(f"  → {ruta}: {len(usados)} secreto(s) → _gcred() · compila ✓")
        if ver:
            limpiados += 1
            continue
        st, r = api("PUT", f"/repos/{REPO}/contents/{ruta}",
                    {"message": f"Quitar credenciales incrustadas de {ruta}",
                     "content": base64.b64encode(nuevo.encode()).decode(),
                     "branch": RAMA, "sha": sha})
        if st in (200, 201):
            limpiados += 1
        else:
            omitidos += 1
            print(f"     ✗ HTTP {st} {str(r)[:90]}")
    # secretos en archivos que no son .py (sólo se reportan)
    for ruta in rutas:
        if ruta.endswith((".py", ".png", ".jpg", ".pdf", ".xlsx", ".db", ".zip", ".gz", ".apk", ".keystore")):
            continue
        txt, _ = traer(ruta)
        if txt and any(re.search(p, txt) for p, _ in PATRONES):
            otros.append(ruta)
    if otros:
        print(f"  ⚠️ con secretos y NO son .py (revisar a mano): {otros}")
    print(f"\n  limpiados: {limpiados} · omitidos: {omitidos}")

    print("\n── 2) archivos de credenciales ──")
    for nombre in BORRAR:
        _, sha = traer(nombre)
        if sha is None:
            print(f"  = {nombre}: ya no está"); continue
        print(f"  → {nombre}: borrar")
        if ver:
            continue
        st, r = api("DELETE", f"/repos/{REPO}/contents/{nombre}",
                    {"message": f"Eliminar {nombre} (credenciales fuera del repo)",
                     "branch": RAMA, "sha": sha})
        print(f"     {'✓ borrado' if st == 200 else '✗ HTTP %d' % st}")

    print("\n── 3) .gitignore ──")
    txt, sha = traer(".gitignore")
    falta = [l for l in ("credentials.json", "token_final.json", "oauth_state.json",
                         "google_token.json", "*.keystore", "*.apk")
             if txt is None or l not in txt]
    if not falta:
        print("  = ya están excluidos")
    else:
        print(f"  → agregar: {falta}")
        if not ver:
            nuevo = (txt or "") + "\n# Credenciales y artefactos: nunca al repo\n" + "\n".join(falta) + "\n"
            st, r = api("PUT", f"/repos/{REPO}/contents/.gitignore",
                        {"message": "gitignore: excluir credenciales de Google",
                         "content": base64.b64encode(nuevo.encode()).decode(),
                         "branch": RAMA, **({"sha": sha} if sha else {})})
            print(f"     {'✓ actualizado' if st in (200, 201) else '✗ HTTP %d' % st}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
