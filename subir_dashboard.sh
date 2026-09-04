#!/bin/bash
# subir_dashboard.sh — Publica el dashboard actualizado en GitHub Pages
TOKEN=$(grep '^GITHUB_TOKEN=' ~/.hermes/.env | cut -d= -f2-)
B64=$(base64 -w0 "$HOME/auditorias_bpg/Dashboard_Auditorias_BPG_ICA.html")
# obtener sha actual del archivo en el repo (si existe)
SHA=$(curl -s -m 20 -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/kaxtillo/bot-bpg-ica/contents/dashboard/index.html" | python3 -c "import json,sys;print(json.load(sys.stdin).get('sha',''))" 2>/dev/null)
# construir JSON payload
python3 - "$TOKEN" "$B64" "$SHA" <<'PYEOF'
import json,sys,urllib.request
token,b64,sha=sys.argv[1],sys.argv[2],sys.argv[3]
payload={"message":"Actualizar dashboard BPG (auto)","content":b64}
if sha: payload["sha"]=sha
req=urllib.request.Request("https://api.github.com/repos/kaxtillo/bot-bpg-ica/contents/dashboard/index.html",
  method="PUT",data=json.dumps(payload).encode(),
  headers={"Authorization":f"Bearer {token}","Content-Type":"application/json","Accept":"application/vnd.github+json"})
try:
    urllib.request.urlopen(req); print("OK")
except urllib.error.HTTPError as e:
    print(f"ERR {e.code}")
PYEOF