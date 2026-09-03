#!/bin/bash
# sincronizar_todo.sh — Sincroniza TODA la cadena de datos y avisa solo si hubo
# un cambio real (nuevo predio/auditoría o mapa actualizado).
#   BD local → Google Sheets → GeoJSON → Mapa UMap → respaldo
# Silencioso si no hubo cambios (para cron no_agent).
cd "$HOME/auditorias_bpg" || exit 1
PY="$HOME/.hermes/hermes-agent/venv/bin/python"
MENSAJES=""

estado() {  # conteo predios|auditorias
    sqlite3 "$HOME/auditorias_bpg/auditorias_bpg.db" \
      "SELECT COUNT(*)||'|'||(SELECT COUNT(*) FROM auditorias) FROM predios;"
}
ANTES=$(estado)
GEOG_ANTES=$(md5sum predios_bpg_ica.geojson 2>/dev/null | cut -d' ' -f1)
DASH_ANTES=$(md5sum Dashboard_Auditorias_BPG_ICA.html 2>/dev/null | cut -d' ' -f1)

# 1. BD ↔ Google Sheets
$PY sincronizar_hoja.py >/tmp/sync_hoja.log 2>&1

# 2. BD → GeoJSON → subir mapa (solo si cambió)
$PY generar_geojson.py >/dev/null 2>&1
GEOG_DESPUES=$(md5sum predios_bpg_ica.geojson 2>/dev/null | cut -d' ' -f1)

# 3. Regenerar dashboard HTML (determinista: solo cambia si cambian los datos)
$PY generar_dashboard.py >/dev/null 2>&1
DASH_DESPUES=$(md5sum Dashboard_Auditorias_BPG_ICA.html 2>/dev/null | cut -d' ' -f1)

# 3. Respaldo diario
HOY=$(date +%Y%m%d)
if [ ! -f backups/bot-bpg-backup-$HOY*.tar.gz ]; then
    bash backup_bot.sh >/dev/null 2>&1
    MENSAJES+="💾 Respaldo automático creado\n"
fi

DESPUES=$(estado)
N_PREDIOS=$(python3 -c "import json;print(len(json.load(open('predios_bpg_ica.geojson'))['features']))" 2>/dev/null)

if [ "$ANTES" != "$DESPUES" ]; then
    MENSAJES+="📊 Google Sheets ↔ BD sincronizadas\n"
fi
if [ "$GEOG_ANTES" != "$GEOG_DESPUES" ]; then
    bash subir_mapa.sh >/dev/null 2>&1
    MENSAJES+="🗺️ Mapa uMap actualizado ($N_PREDIOS predios)\n"
fi
if [ "$DASH_ANTES" != "$DASH_DESPUES" ]; then
    MENSAJES+="📈 Dashboard HTML actualizado\n"
fi

if [ -n "$MENSAJES" ]; then
    echo -e "✅ Sincronización completa:\n${MENSAJES}📋 BD: $(echo $DESPUES | tr '|' ' predios, ') auditorías"
else
    exit 0  # silencio: sin cambios
fi