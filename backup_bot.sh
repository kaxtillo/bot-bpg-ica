#!/bin/bash
# backup_bot.sh - Respaldo completo del bot BPG para migración
# Uso: bash backup_bot.sh
# Genera: /tmp/bot-bpg-backup-YYYYMMDD.tar.gz

set -e

BACKUP_DIR="/home/ubuntu/bot-bpg-backup-$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "  RESPALDO BOT BPG - $(date)"
echo "=========================================="

# 1. Configuración completa de OpenClaw (incluye tokens)
echo "[1/6] Respaldando configuración de OpenClaw..."
cp -r /home/ubuntu/.openclaw "$BACKUP_DIR/openclaw-config" 2>/dev/null || \
  rsync -a /home/ubuntu/.openclaw/ "$BACKUP_DIR/openclaw-config/" --exclude='workspace' --exclude='completions' --exclude='logs' --exclude='media' --exclude='canvas' --exclude='browser'

# 2. Workspace (PDFs, scripts, memoria)
echo "[2/6] Respaldando workspace..."
cp -r /home/ubuntu/.openclaw/workspace "$BACKUP_DIR/workspace" 2>/dev/null

# 3. Dependencias Python
echo "[3/6] Respaldando dependencias Python..."
pip3 freeze --break-system-packages > "$BACKUP_DIR/pip-requirements.txt" 2>/dev/null || \
  pip3 freeze > "$BACKUP_DIR/pip-requirements.txt" 2>/dev/null || \
  echo "No se pudieron exportar dependencias pip" > "$BACKUP_DIR/pip-requirements.txt"

# 4. Versión e info de OpenClaw
echo "[4/6] Guardando versiones..."
openclaw --version 2>/dev/null > "$BACKUP_DIR/version.txt" || echo "openclaw no encontrado" > "$BACKUP_DIR/version.txt"
npm list -g --depth=0 2>/dev/null > "$BACKUP_DIR/npm-global.txt" || true

# 5. Script de instalación para nuevo servidor
echo "[5/6] Creando guía de instalación..."
cat > "$BACKUP_DIR/INSTALAR_NUEVO_SERVIDOR.md" << 'EOF'
# Instalación en nuevo servidor

## Prerrequisitos
- Ubuntu 22.04+ o Debian 12+
- Node.js 22+ (npm)
- Python 3.10+
- ffmpeg (para transcripción de audio)

## Pasos

```bash
# 1. Instalar OpenClaw
curl -fsSL https://openclaw.ai/install.sh | bash

# 2. Instalar dependencias Python
sudo apt install -y ffmpeg
pip3 install fpdf2 SpeechRecognition pydub faster-whisper --break-system-packages

# 3. Clonar workspace
git clone https://github.com/kaxtillo/bot-bpg-ica.git
rm -rf /home/ubuntu/.openclaw/workspace
mv bot-bpg-ica /home/ubuntu/.openclaw/workspace

# 4. Restaurar configuración con tokens
# (desde el backup .tar.gz que contiene openclaw-config/)
tar xzf bot-bpg-backup-*.tar.gz
cp -r openclaw-config/* /home/ubuntu/.openclaw/

# 5. Iniciar OpenClaw
openclaw gateway start
```

## Configurar Telegram
```bash
openclaw telegram connect
# Escanear QR con la app
```
EOF

# 6. Comprimir todo
echo "[6/6] Comprimiendo respaldo..."
cd /home/ubuntu
tar czf "/tmp/bot-bpg-backup-$(date +%Y%m%d).tar.gz" \
  -C /home/ubuntu "bot-bpg-backup-$(date +%Y%m%d)"

# Limpiar
rm -rf "$BACKUP_DIR"

echo "=========================================="
echo "  ✅ RESPALDO COMPLETO"
echo "=========================================="
echo "Archivo: /tmp/bot-bpg-backup-$(date +%Y%m%d).tar.gz"
echo "Tamaño: $(du -h /tmp/bot-bpg-backup-$(date +%Y%m%d).tar.gz | cut -f1)"
echo "Para migrar: subir este .tar.gz al nuevo servidor y seguir INSTALAR_NUEVO_SERVIDOR.md"
