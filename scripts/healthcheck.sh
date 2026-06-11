#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=/home/ubuntu/whatsapp-api-server
LOG_DIR="$PROJECT_DIR/logs"
HEALTH_LOG="$LOG_DIR/healthcheck_events.log"
HEALTH_METRICS="$LOG_DIR/healthcheck_metrics.json"
MAX_LOG_SIZE=5242880  # 5MB

mkdir -p "$LOG_DIR"

# Rotação de logs quando atingir tamanho máximo
rotate_log() {
  local log_file="$1"
  if [ -f "$log_file" ]; then
    local size=$(stat -c%s "$log_file" 2>/dev/null || echo 0)
    if [ "$size" -gt "$MAX_LOG_SIZE" ]; then
      mv "$log_file" "${log_file}.$(date +%s)"
      gzip "${log_file}".* 2>/dev/null || true
    fi
  fi
}

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TIMESTAMP_EPOCH=$(date +%s)

# Healthcheck com timeout otimizado (5 segundos)
HTTP_CODE=$(curl -sS -m 5 -o /tmp/whatsapp_api_health.json -w '%{http_code}' http://127.0.0.1:8000/health 2>/dev/null || echo "000")
RESPONSE_TIME=$(curl -sS -m 5 -w '%{time_total}' -o /dev/null http://127.0.0.1:8000/health 2>/dev/null || echo "0")

# Registrar métrica em JSON para análise
echo "{\"timestamp\":\"$TIMESTAMP\",\"epoch\":$TIMESTAMP_EPOCH,\"http_code\":$HTTP_CODE,\"response_time\":$RESPONSE_TIME}" >> "$HEALTH_METRICS"

if [ "$HTTP_CODE" != "200" ]; then
  echo "$TIMESTAMP [FAILED] http_code=$HTTP_CODE response_time=${RESPONSE_TIME}s" | tee -a "$HEALTH_LOG"
  
  # Tentar reiniciar apenas se falhas consecutivas > 2
  RECENT_FAILURES=$(tail -3 "$HEALTH_LOG" 2>/dev/null | grep -c "FAILED" || echo "0")
  if [ "$RECENT_FAILURES" -ge 2 ]; then
    echo "$TIMESTAMP [ACTION] Restarting service after $RECENT_FAILURES consecutive failures" | tee -a "$HEALTH_LOG"
    sudo systemctl restart whatsapp-api.service 2>&1 | tee -a "$HEALTH_LOG"
  fi
  exit 1
fi

echo "$TIMESTAMP [OK] http_code=$HTTP_CODE response_time=${RESPONSE_TIME}s" >> "$HEALTH_LOG"

# Rotação de logs
rotate_log "$HEALTH_LOG"
rotate_log "$HEALTH_METRICS"
