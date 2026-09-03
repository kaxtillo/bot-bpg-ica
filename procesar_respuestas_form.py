#!/usr/bin/env python3
"""
Procesa las respuestas del formulario "Auditoría BPG ICA - Resolución 067449"
y las consolida en la base de datos local (→ Google Sheets → mapa).

Uso:
  python3 procesar_respuestas_form.py            # procesa respuestas nuevas
  python3 procesar_respuestas_form.py --ver      # solo lista respuestas
  python3 procesar_respuestas_form.py --todo     # reprocesa TODAS las respuestas
"""
import json
import os
import re
import subprocess
import sys

BASE = os.path.expanduser("~/auditorias_bpg")
MAPEO = os.path.join(BASE, "form_mapeo.json")
GUARDAR = os.path.join(BASE, "guardar_auditoria.py")
PROCESADAS = os.path.join(BASE, "form_respuestas_procesadas.json")
PY = "/home/hermes/.hermes/hermes-agent/venv/bin/python"

# títulos de los campos de datos del predio en el formulario
DATOS = {
    "Fecha de la auditoría": "fecha",
    "Nombre del predio": "predio",
    "Propietario": "propietario",
    "Identificación / Cédula": "identificacion",
    "Teléfono": "telefono",
    "Municipio": "municipio",
    "Vereda": "vereda",
    "GPS (latitud, longitud)": "gps",
}


def cargar_credenciales():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    tok = json.load(open(os.path.expanduser("~/.hermes/google_token.json")))
    creds = Credentials(
        token=tok.get("token"), refresh_token=tok.get("refresh_token"),
        token_uri=tok.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=tok.get("client_id"), client_secret=tok.get("client_secret"),
        scopes=["https://www.googleapis.com/auth/forms.responses.readonly",
                "https://www.googleapis.com/auth/forms.body", "https://www.googleapis.com/auth/drive"])
    # Refrescar SIEMPRE: el token local puede parecer válido pero estar revocado
    # en el servidor (HTTP 401). Forzar refresh garantiza un access token fresco.
    creds.refresh(Request())
    # persistir el access token renovado para el siguiente run
    try:
        tok["token"] = creds.token
        tok["expiry"] = creds.expiry.isoformat() if creds.expiry else None
        json.dump(tok, open(os.path.expanduser("~/.hermes/google_token.json"), "w"))
    except Exception:
        pass
    return creds


def obtener_respuestas(creds, fid):
    import urllib.request
    req = urllib.request.Request(f"https://forms.googleapis.com/v1/forms/{fid}/responses",
                                 headers={"Authorization": f"Bearer {creds.token}"})
    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode())


def extraer_id_criterio(titulo):
    m = re.match(r"^(\d+\.\d+)\.", titulo)
    return m.group(1) if m else None


def respuesta_a_payload(resp, mapeo, invertido):
    """Convierte una respuesta del form a payload de auditoría."""
    datos_predio = {}
    detalle = {}
    answers = resp.get("answers", {})
    for qid, info in answers.items():
        valor = info["textAnswers"]["answers"][0]["value"].strip()
        titulo = invertido.get(qid, "")
        cid = extraer_id_criterio(titulo)
        if cid:
            # respuesta de criterio: Sí/No/No aplica -> SI/NO/NA
            v = {"Sí": "SI", "No": "NO", "No aplica": "NA"}.get(valor)
            if v:
                detalle[cid] = v
        elif titulo in DATOS:
            campo = DATOS[titulo]
            if campo == "fecha" and valor:
                # el form devuelve fecha en formato YYYY-MM-DD (o con año)
                pass
            datos_predio[campo] = valor
    # fecha por defecto
    fecha = datos_predio.get("fecha") or resp.get("lastSubmittedTime", "")[:10]
    payload = {**datos_predio, "fecha": fecha, "departamento": "Cauca",
               "detalle_puntos": detalle}
    return payload


def main():
    mapeo = json.load(open(MAPEO))
    fid = mapeo["form_id"]
    mapeo_t = mapeo["mapeo"]
    invertido = {v: k for k, v in mapeo_t.items()}

    creds = cargar_credenciales()
    data = obtener_respuestas(creds, fid)
    respuestas = data.get("responses", [])

    if "--ver" in sys.argv:
        print(f"📋 Respuestas en el formulario: {len(respuestas)}")
        for r in respuestas:
            print(f"  • {r.get('responseId','?')} — {r.get('lastSubmittedTime','')[:16]}")
        return

    # cargar respuestas ya procesadas (para no re-procesar en el cron)
    ya = set()
    if os.path.exists(PROCESADAS):
        ya = set(json.load(open(PROCESADAS)).get("procesadas", []))

    nuevas = [r for r in respuestas if r.get("responseId") not in ya]
    if not nuevas:
        return  # silencio total (para cron no_agent: sin salida = sin mensaje)

    procesadas = 0
    saltadas = 0
    nuevos_ids = []
    for r in nuevas:
        payload = respuesta_a_payload(r, mapeo, invertido)
        n_crit = len(payload.get("detalle_puntos", {}))
        if n_crit < 30:
            print(f"  ⏭️  Respuesta incompleta ({n_crit}/62 criterios) — se omite")
            saltadas += 1
            nuevos_ids.append(r["responseId"])  # no re-intentar incompletas
            continue
        tmp = "/tmp/respuesta_form.json"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        rproc = subprocess.run([PY, GUARDAR, tmp], capture_output=True, text=True)
        if rproc.returncode == 0:
            procesadas += 1
            nuevos_ids.append(r["responseId"])
            print(f"  ✅ Guardada: {payload.get('predio','?')} ({n_crit} criterios)")
        else:
            print(f"  ❌ Error guardando: {rproc.stderr[-200:]}")

    if nuevos_ids:
        ya.update(nuevos_ids)
        json.dump({"procesadas": sorted(ya)}, open(PROCESADAS, "w"))

    print(f"\n✅ Procesadas: {procesadas} · Incompletas: {saltadas}")
    if procesadas:
        # sincronizar la hoja principal
        print("🔄 Sincronizando con Google Sheets...")
        subprocess.run([PY, os.path.join(BASE, "sincronizar_hoja.py")], capture_output=True, text=True)
        print("   Hoja actualizada.")


if __name__ == "__main__":
    main()
