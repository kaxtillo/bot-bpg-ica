#!/usr/bin/env bash
# procesar_kobo_publicar.sh — Importa submissions nuevas de KoboToolbox y republica.
#
# Pensado para cron cada 3 horas (no_agent: stdout vacío = no se envía nada).
#   - Si no hay auditorías nuevas: SILENCIO TOTAL.
#   - Si hay: importa y corre el pipeline (hoja, GeoJSON, uMap, dashboard, respaldo),
#     y devuelve un resumen para Telegram.
set -uo pipefail

PY=/home/hermes/.hermes/hermes-agent/venv/bin/python
BASE=/home/hermes/auditorias_bpg
DB=$BASE/auditorias_bpg.db

cuenta() { "$PY" -c "import sqlite3;print(sqlite3.connect('$DB').execute('SELECT COUNT(*) FROM auditorias').fetchone()[0])" 2>/dev/null || echo 0; }

ANTES=$(cuenta)
SALIDA_KOBO=$("$PY" "$BASE/procesar_kobo.py" 2>&1)
RC=$?
DESPUES=$(cuenta)

# ¿llegó algo nuevo? (o hubo error que merezca aviso)
NUEVAS=$((DESPUES - ANTES))

if [ "$RC" -ne 0 ]; then
    echo "⚠️ Error procesando Kobo (código $RC):"
    echo "$SALIDA_KOBO" | tail -5
    exit 0
fi

if [ "$NUEVAS" -le 0 ]; then
    exit 0   # sin novedades → silencio
fi

# Hay datos nuevos: publicar
SALIDA_SYNC=$(bash "$BASE/sincronizar_todo.sh" 2>&1)

echo "📥 KoboToolbox: $NUEVAS auditoría(s) nueva(s) importada(s) · $(date '+%d/%m %H:%M')"
echo "$SALIDA_KOBO" | grep -E "guardado|guardada|✅" | tail -4
echo "---"
echo "$SALIDA_SYNC" | grep -vE "^$" | tail -6
