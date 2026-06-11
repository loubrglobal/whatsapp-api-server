#!/usr/bin/env bash
set -euo pipefail

# Script para atualizar crontab com healthcheck otimizado a cada 5 minutos

PROJECT_DIR=/home/ubuntu/whatsapp-api-server

echo "Atualizando crontab para healthcheck a cada 5 minutos..."

# Remover jobs antigos (15 minutos)
crontab -l 2>/dev/null | grep -v "healthcheck.sh" > /tmp/crontab_new.txt || true

# Adicionar novo job (5 minutos)
echo "*/5 * * * * $PROJECT_DIR/scripts/healthcheck.sh >> $PROJECT_DIR/logs/cron.log 2>&1" >> /tmp/crontab_new.txt

# Adicionar relatório diário (mantém o existente)
echo "0 9 * * * python3 $PROJECT_DIR/scripts/generate_report.py >> $PROJECT_DIR/logs/report.log 2>&1" >> /tmp/crontab_new.txt

# Instalar novo crontab
crontab /tmp/crontab_new.txt
rm /tmp/crontab_new.txt

echo "✅ Crontab atualizado com sucesso!"
echo ""
echo "Cronograma atual:"
crontab -l | grep -E "healthcheck|generate_report"
