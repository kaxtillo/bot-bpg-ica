#!/usr/bin/env bash
# Backup de la configuración funcional del bot auditor BPG ICA (Hermes).
# Genera ~/auditorias_bpg/backups/bot-bpg-backup-<fecha>.tar.gz
set -euo pipefail

FECHA=$(date +%Y%m%d_%H%M%S)
DEST=~/auditorias_bpg/backups/bot-bpg-backup-${FECHA}.tar.gz
mkdir -p ~/auditorias_bpg/backups
cd "$HOME"   # base de rutas relativas del tar

echo "📦 Creando respaldo en: ${DEST}"

# 1) Base de datos de consolidación
# 2) Scripts del sistema de auditoría
# 3) Skill de auditoría BPG
# 4) Repo del bot anterior (workspace de referencia)
# 5) Configuración de Hermes (config.yaml + .env — con permisos restrictivos)
tar czf "${DEST}" \
  -C ~ \
  auditorias_bpg/auditorias_bpg.db \
  auditorias_bpg/*.py \
  auditorias_bpg/*.sh \
  auditorias_bpg/*.csv \
  auditorias_bpg/*.geojson \
  auditorias_bpg/resumen_sistema_auditor_bpg_ica.md \
  .hermes/skills/productivity/bpg-ica-audits \
  Proyectos/bot-bpg-ica \
  .hermes/config.yaml \
  .hermes/.env 2>/dev/null || true

chmod 600 "${DEST}"
echo "✅ Respaldo completado:"
ls -lh "${DEST}"

# Limpiar backups antiguos (conservar los 5 más recientes)
ls -t ~/auditorias_bpg/backups/bot-bpg-backup-*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
echo "🗑️  Backups antiguos (>5) eliminados automáticamente."
