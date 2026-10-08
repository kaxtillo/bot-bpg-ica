#!/usr/bin/env python3
"""
Integra KoboToolbox → Base de datos BPG ICA.

Descarga las respuestas (submissions) de los formularios de auditoría BPG desde
la API de KoboToolbox, extrae SOLO los 62 criterios (c_1_1 … c_10_2) más los datos
de identificación del predio, y consolida en la BD con guardar_auditoria.py
(luego Google Sheets y mapa vía los flujos habituales).

Soporta varios formularios (V1 y V2) con registro de procesadas INDEPENDIENTE
por formulario, para que un formulario nuevo no se confunda con el histórico.

Requisitos:
  - Token de API de KoboToolbox en ~/.hermes/.env como KOBO_TOKEN
    (kf.kobotoolbox.org → Cuenta → API Key)
  - UID(s) del formulario. Se configuran en FORMS o con la variable de entorno
    KOBO_FORM_UIDS (uids separados por coma).

Uso:
  python3 procesar_kobo.py --ver       # listar submissions de cada formulario, sin guardar
  python3 procesar_kobo.py             # procesar y guardar las nuevas (silencio si no hay)
"""
import json, os, re, subprocess, sys, urllib.request

BASE = os.path.expanduser("~/auditorias_bpg")
GUARDAR = os.path.join(BASE, "guardar_auditoria.py")
PROCESADAS = os.path.join(BASE, "kobo_submissions_procesadas.json")
PY = "/home/hermes/.hermes/hermes-agent/venv/bin/python"

# ── Formularios soportados ────────────────────────────────────────────────
# El registro de submissions procesadas es POR FORMULARIO (uid), de modo que
# añadir un formulario nuevo no reprocesa ni pisa el histórico de otro.
FORMS = [
    {"uid": "aNVGYKhswB8hFBSArTh8b8", "label": "Auditoría BPG (V1)"},
    {"uid": "a78ZWXkFgDUNVrDPtc44dG", "label": "Auditoría BPG ICA - V2"},
]
# Permite override total: KOBO_FORM_UIDS="uid1,uid2"
_env_uids = os.environ.get("KOBO_FORM_UIDS") or os.environ.get("KOBO_FORM_UID")
if _env_uids:
    FORMS = [{"uid": u.strip(), "label": u.strip()} for u in _env_uids.split(",") if u.strip()]

KOBO_API = os.environ.get("KOBO_API", "https://kf.kobotoolbox.org/api/v2")


def leer_token():
    env = os.path.expanduser("~/.hermes/.env")
    for line in open(env):
        if line.startswith("KOBO_TOKEN="):
            return line.strip().split("=", 1)[1]
    return os.environ.get("KOBO_TOKEN", "")


def get_submissions(token, uid):
    url = f"{KOBO_API}/assets/{uid}/data/?format=json&limit=500"
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
    """Extrae SOLO los 62 criterios (c_X_Y) + datos de identificación del predio."""
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


def cargar_registro():
    """{uid: [ids procesadas]}. Migra el formato antiguo (lista plana → primer formulario)."""
    if not os.path.exists(PROCESADAS):
        return {}
    data = json.load(open(PROCESADAS))
    proc = data.get("procesadas", [])
    if isinstance(proc, dict):
        return {k: [str(x) for x in v] for k, v in proc.items()}
    # formato antiguo: lista plana → asignar al primer formulario (V1)
    return {FORMS[0]["uid"]: [str(x) for x in proc]}


def guardar_registro(reg):
    json.dump({"procesadas": {uid: sorted(set(ids)) for uid, ids in reg.items()}},
              open(PROCESADAS, "w"), indent=1)


def main():
    token = leer_token()
    if not token:
        print("❌ Falta KOBO_TOKEN en ~/.hermes/.env"); return

    ver = "--ver" in sys.argv
    reg = cargar_registro()

    if ver:
        for f in FORMS:
            try:
                subs = get_submissions(token, f["uid"]).get("results", [])
            except Exception as e:
                print(f"⚠️  {f['label']} ({f['uid']}): error {e}"); continue
            ya = set(reg.get(f["uid"], []))
            print(f"\n=== {f['label']} ({f['uid']}) — {len(subs)} submission(s), "
                  f"{len(subs) - len([s for s in subs if str(s.get('_id')) in ya])} nueva(s) ===")
            for s in subs:
                estado = "procesada" if str(s.get("_id")) in ya else "NUEVA"
                crit = len([1 for k in s if re.search(r"c_\d+_\d+", k)])
                print(f"  • [{estado}] {s.get('nombre_predio','?')} — {s.get('fecha','')} "
                      f"— {crit} criterios — _id={s.get('_id')}")
        return

    total_ok, total_err, hubo_nuevas = 0, 0, False
    for f in FORMS:
        try:
            subs = get_submissions(token, f["uid"]).get("results", [])
        except Exception as e:
            print(f"⚠️  {f['label']}: error de descarga ({e})"); continue
        ya = set(reg.get(f["uid"], []))
        nuevas = [s for s in subs if str(s.get("_id")) not in ya]
        if not nuevas:
            continue
        hubo_nuevas = True
        for s in nuevas:
            payload = a_payload(s)
            if not payload["detalle_puntos"]:
                continue  # sin criterios → no es una auditoría
            tmp = f"/tmp/kobo_{f['uid']}_{s.get('_id')}.json"
            json.dump(payload, open(tmp, "w"), ensure_ascii=False)
            r = subprocess.run([PY, GUARDAR, tmp], capture_output=True, text=True)
            if r.returncode == 0:
                ya.add(str(s.get("_id"))); total_ok += 1
                print(f"✅ {payload['predio']} guardado ({f['label']}, "
                      f"{len(payload['detalle_puntos'])} criterios)")
            else:
                total_err += 1
                print(f"❌ {payload['predio']} ({f['label']}): {r.stderr[-300:]}")
                os.remove(tmp)
        reg[f["uid"]] = sorted(ya)

    guardar_registro(reg)
    if hubo_nuevas:
        print(f"Resumen: {total_ok} guardado(s) · {total_err} con error")
    # si no hubo nada nuevo → silencio (apto para cron no_agent)


if __name__ == "__main__":
    main()
