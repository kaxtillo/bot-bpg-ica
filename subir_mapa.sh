#!/usr/bin/env bash
# Auto-actualiza el GeoJSON del mapa en GitHub (repo bot-bpg-ica, carpeta mapa/).
# Sin cambios → silencio (exit 0). Con cambios → sube y avisa.
# Pensado para cron: stdout vacío = nada que reportar.
set -euo pipefail

REPO="kaxtillo/bot-bpg-ica"
RUTA="mapa/predios_bpg_ica.geojson"
ARCHIVO=~/auditorias_bpg/predios_bpg_ica.geojson
TOKEN=$(grep '^GITHUB_TOKEN=' ~/.hermes/.env | cut -d= -f2-)

# 1) Regenerar el GeoJSON desde la base de datos
python3 ~/auditorias_bpg/generar_geojson.py >/dev/null 2>&1

# 2) Obtener estado remoto
REMOTO=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
  "https://api.github.com/repos/${REPO}/contents/${RUTA}")
SHA=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" <<< "${REMOTO}")
REMOTE_B64=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('content','').replace(chr(10),''))" <<< "${REMOTO}")
LOCAL_B64=$(base64 -w0 "${ARCHIVO}")

# 3) ¿Cambió algo? (si no se pudo leer el remoto, NO asumir "sin cambios")
if [ -z "${REMOTE_B64}" ]; then
  echo "⚠️  No se pudo leer el estado remoto del mapa (GET falló). Reintentando..."
  sleep 2
  REMOTO=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
    "https://api.github.com/repos/${REPO}/contents/${RUTA}")
  SHA=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" <<< "${REMOTO}")
  REMOTE_B64=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('content','').replace(chr(10),''))" <<< "${REMOTO}")
fi
if [ -z "${REMOTE_B64}" ]; then
  echo "⚠️  Error: no se pudo leer el archivo remoto (¿token sin acceso?). No se sube nada."
  exit 1
fi
if [ "${LOCAL_B64}" = "${REMOTE_B64}" ]; then
  exit 0  # sin cambios → silencio
fi

# 4) Subir (crear o actualizar con sha)
BODY=$(python3 - <<EOF
import json
json.dump({"message": "Mapa BPG ICA auto-actualizado", "content": "${LOCAL_B64}", "sha": "${SHA}"}, open("/tmp/subir_mapa_body.json", "w"))
EOF
)
HTTP=$(curl -s -o /tmp/subir_mapa_resp.json -w "%{http_code}" -X PUT \
  -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/contents/${RUTA}" \
  -d @/tmp/subir_mapa_body.json)

if [ "${HTTP}" = "200" ] || [ "${HTTP}" = "201" ]; then
  echo "🗺️  Mapa BPG ICA actualizado: $(date '+%Y-%m-%d %H:%M')"
  echo "🔗 https://raw.githubusercontent.com/${REPO}/main/${RUTA}"
else
  echo "⚠️  Error subiendo el mapa (HTTP ${HTTP})"
  exit 1
fi
