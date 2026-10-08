#!/usr/bin/env python3
"""
subir_repo.py — Sincroniza los scripts locales con el repo de GitHub (kaxtillo/bot-bpg-ica).

Sin git: uses the contents API (el `git push` falla con el token, y la API es más simple).
Compara el sha del blob de git de cada archivo local contra el que tiene GitHub:
igual → no gasta una petición de subida; distinto → PUT (crea o actualiza con sha).

Nunca sube datos sensibles ni archivos generados: ver EXCLUIR.
Uso: subir_repo.py [--ver]   (--ver = sólo mostrar qué cambiaría)
"""
import base64, hashlib, json, os, sys, urllib.error, urllib.request

REPO = "kaxtillo/bot-bpg-ica"
RAMA = "main"
BASE = os.path.expanduser("~/auditorias_bpg")
EXTENSIONES = (".py", ".sh", ".js")
# nunca subir: secretos y artefactos (los PDF pueden llevar datos personales)
EXCLUIR = ("credentials", "token_final", "oauth_state", "client_secret", ".env",
           "auditorias_bpg.db", ".pdf", ".csv", ".keystore", ".apk")
ENV = os.path.expanduser("~/.hermes/.env")


def token():
    for l in open(ENV):
        if l.startswith("GITHUB_TOKEN="):
            return l.split("=", 1)[1].strip()
    raise SystemExit("falta GITHUB_TOKEN en ~/.hermes/.env")


T = token()


def api(metodo, ruta, cuerpo=None):
    url = "https://api.github.com" + ruta
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    q = urllib.request.Request(url, method=metodo, data=datos,
                               headers={"Authorization": "Bearer " + T,
                                        "Accept": "application/vnd.github+json",
                                        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(q, timeout=90) as r:
            b = r.read().decode()
            return r.status, (json.loads(b) if b.strip().startswith(("{", "[")) else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:200]}


def sha_git(datos: bytes) -> str:
    """sha del blob de git (es el que GitHub muestra como 'sha' del archivo)."""
    cabecera = b"blob %d\0" % len(datos)
    return hashlib.sha1(cabecera + datos).hexdigest()


def a_subir():
    archivos = []
    for n in sorted(os.listdir(BASE)):
        if not n.endswith(EXTENSIONES):
            continue
        if any(x in n for x in EXCLUIR):
            continue
        ruta = os.path.join(BASE, n)
        if not os.path.isfile(ruta):
            continue
        archivos.append((n, ruta))
    return archivos


def main():
    solo_ver = "--ver" in sys.argv
    print(f"Subiendo scripts a {REPO} ({'SIMULACIÓN' if solo_ver else 'real'})\n")
    subidos = iguales = errores = 0
    for nombre, ruta in a_subir():
        crudo = open(ruta, "rb").read()
        local_sha = sha_git(crudo)
        st, info = api("GET", f"/repos/{REPO}/contents/{nombre}?ref={RAMA}")
        remoto_sha = info.get("sha") if st == 200 else ""
        if remoto_sha == local_sha:
            iguales += 1
            print(f"  = {nombre:<34} sin cambios")
            continue
        accion = "nuevo" if st != 200 else "actualizar"
        if solo_ver:
            print(f"  → {nombre:<34} {accion} ({len(crudo)} bytes)")
            subidos += 1
            continue
        cuerpo = {"message": f"{'Agregar' if st != 200 else 'Actualizar'} {nombre}",
                  "content": base64.b64encode(crudo).decode(),
                  "branch": RAMA}
        if remoto_sha:
            cuerpo["sha"] = remoto_sha
        st2, resp = api("PUT", f"/repos/{REPO}/contents/{nombre}", cuerpo)
        if st2 in (200, 201):
            subidos += 1
            print(f"  ✓ {nombre:<34} {accion} (HTTP {st2})")
        else:
            errores += 1
            print(f"  ✗ {nombre:<34} HTTP {st2} {str(resp)[:90]}")
    print(f"\n  subidos/actualizados: {subidos} · ya iguales: {iguales} · errores: {errores}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
