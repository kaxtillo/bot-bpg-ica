#!/usr/bin/env python3
"""
Integra KoboToolbox → Base de datos BPG ICA.

Descarga las respuestas (submissions) del formulario de auditoría BPG desde
la API de KoboToolbox, las convierte al formato de guardar_auditoria.py
(detalle_puntos con SI/NO/NA + datos del predio) y consolida en la BD
(luego Google Sheets y mapa vía los flujos habituales).

Requisitos:
  - Token de API de KoboToolbox en ~/.hermes/.env como KOBO_TOKEN
    (kf.kobotoolbox.org → Cuenta → API Key)
  - UID del formulario (el id "aqZR..." del formulario desplegado)

Uso:
  python3 procesar_kobo.py --ver       # listar submissions sin guardar
  python3 procesar_kobo.py             # procesar y guardar las nuevas
"""
import base64, json, os, re, subprocess, sys, urllib.request

BASE = os.path.expanduser("~/auditorias_bpg")
GUARDAR = os.path.join(BASE, "guardar_auditoria.py")
PROCESADAS = os.path.join(BASE, "kobo_submissions_procesadas.json")
PY = "/home/hermes/.hermes/hermes-agent/venv/bin/python"

# Configuración (ajustar)
FORM_UID = os.environ.get("KOBO_FORM_UID", "aNVGYKhswB8hFBSArTh8b8")  # "Auditoría BPG"
KOBO_API = os.environ.get("KOBO_API", "https://kc.kobotoolbox.org/api/v2")


def leer_token():
    env = os.path.expanduser("~/.hermes/.env")
    for line in open(env):
        if line.startswith("KOBO_TOKEN="):
            return line.strip().split("=", 1)[1]
    return os.environ.get("KOBO_TOKEN", "")


def get_submissions(token):
    url = f"{KOBO_API}/assets/{FORM_UID}/data/?format=json&limit=500"
    req = urllib.request.Request(url, headers={"Authorization": "Token " + token})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())


def normalizar_valor(v):
    if v is None: return None
    s = str(v).strip().lower()
    if s in ("si", "yes", "1"): return "SI"
    if s in ("no", "0"): return "NO"
    if s in ("no_aplica", "na", "n/a", "nodata"): return "NA"
    return None


def cid_desde_name(name):
    """'c_1_1' o 'seccion_1/c_1_1' -> '1.1'"""
    m = re.search(r"c_(\d+)_(\d+)", name or "")
    if m: return f"{m.group(1)}.{m.group(2)}"
    return None


def a_payload(sub):
    detalle = {}
    for k, v in sub.items():
        cid = cid_desde_name(k)
        nv = normalizar_valor(v)
        if cid and nv:
            detalle[cid] = nv
    gps = sub.get("gps") or ""
    coords = gps.split()[:2]  # formato geopoint: lat lon alt acc
    # Geopoint de KoboToolbox a veces viene como lista "lat lon alt acc" en "gps"
    if not coords and isinstance(gps, (list, tuple)) and len(gps) >= 2:
        coords = [str(gps[0]), str(gps[1])]
    # Coordenadas manuales (latitud_manual / longitud_manual)
    if not coords or not coords[0]:
        lm = sub.get("latitud_manual"); lom = sub.get("longitud_manual")
        if lm not in (None, "") and lom not in (None, ""):
            coords = [str(lm).replace(",", "."), str(lom).replace(",", ".")]
    # KoboToolbox geopoint a veces expone lat/lon por separado
    if not coords or not coords[0]:
        try:
            if isinstance(sub.get("_gps_latitude"), (int, float)):
                coords = [str(sub["_gps_latitude"]), str(sub.get("_gps_longitude", ""))]
        except Exception:
            pass
    p = {
        "predio": (sub.get("nombre_predio") or "").strip(),
        "propietario": (sub.get("propietario") or "").strip(),
        "identificacion": (sub.get("identificacion") or "").strip(),
        "telefono": (sub.get("telefono") or "").strip(),
        "municipio": (sub.get("municipio") or "").strip(),
        "vereda": (sub.get("vereda") or "").strip(),
        "fecha": sub.get("fecha") or "",
        "detalle_puntos": detalle,
    }
    # Solo incluir lat/lon si hay coordenadas válidas (no borrar las existentes)
    if len(coords) >= 2 and coords[0] and coords[1]:
        try:
            p["latitud"] = float(coords[0]); p["longitud"] = float(coords[1])
        except ValueError:
            pass
    return p


def main():
    token = leer_token()
    if not token:
        print("❌ Falta KOBO_TOKEN en ~/.hermes/.env"); return
    if "--ver" in sys.argv:
        data = get_submissions(token)
        subs = data.get("results", [])
        print(f"Submissions en KoboToolbox: {len(subs)}")
        for s in subs:
            print(f"  • {s.get('nombre_predio','?')} — {s.get('_id','')}")
        return
    data = get_submissions(token)
    subs = data.get("results", [])
    ya = set(json.load(open(PROCESADAS)).get("procesadas", [])) if os.path.exists(PROCESADAS) else set()
    nuevas = [s for s in subs if str(s.get("_id")) not in ya]
    if not nuevas:
        return  # silencio para cron
    ok, err = 0, 0
    for s in nuevas:
        payload = a_payload(s)
        tmp = f"/tmp/kobo_{s.get('_id')}.json"
        json.dump(payload, open(tmp, "w"), ensure_ascii=False)
        r = subprocess.run([PY, GUARDAR, tmp], capture_output=True, text=True)
        if r.returncode == 0:
            ya.add(str(s.get("_id"))); ok += 1
            print(f"✅ {payload['predio']} guardado")
        else:
            err += 1; print(f"❌ {payload['predio']}: {r.stderr[-200:]}"); os.remove(tmp)
    json.dump({"procesadas": sorted(ya)}, open(PROCESADAS, "w"))
    print(f"Resumen: {ok} guardado(s) · {err} con error")


if __name__ == "__main__":
    main()