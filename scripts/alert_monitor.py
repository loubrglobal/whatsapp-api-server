#!/usr/bin/env python3
"""
Script de Alertas — Monitora taxa de sucesso e envia notificações
Executa a cada 15 minutos via cron
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path("/home/ubuntu/whatsapp-api-server")
LOGS_DIR = PROJECT_DIR / "logs"
ALERTS_LOG = LOGS_DIR / "alerts.log"
ALERT_THRESHOLD = 95.0  # Taxa mínima de sucesso

def log_alert(message, level="INFO"):
    """Registra alerta em arquivo"""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    log_entry = f"{timestamp} [{level}] {message}"
    print(log_entry)
    with open(ALERTS_LOG, "a") as f:
        f.write(log_entry + "\n")

def fetch_metrics():
    """Busca métricas do endpoint /metrics/all"""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:8000/metrics/all"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        log_alert(f"Erro ao buscar métricas: {e}", "ERROR")
    return None

def check_service_status(metrics):
    """Verifica se o serviço está ativo"""
    if metrics and metrics.get("service", {}).get("is_active"):
        return True
    return False

def check_success_rate(metrics):
    """Verifica taxa de sucesso"""
    if metrics:
        stats = metrics.get("healthcheck", {}).get("stats", {})
        success_rate = stats.get("success_rate", 0)
        return success_rate
    return 0

def check_response_time(metrics):
    """Verifica tempo de resposta"""
    if metrics:
        stats = metrics.get("healthcheck", {}).get("stats", {})
        avg_time = stats.get("avg_response_time", 0)
        return avg_time
    return 0

def main():
    """Executa verificações de alerta"""
    log_alert("Iniciando verificação de alertas", "INFO")
    
    # Buscar métricas
    metrics = fetch_metrics()
    if not metrics:
        log_alert("Não foi possível buscar métricas", "ERROR")
        return 1
    
    # Verificar status do serviço
    if not check_service_status(metrics):
        log_alert("⚠️  ALERTA: Serviço inativo!", "CRITICAL")
        return 1
    
    # Verificar taxa de sucesso
    success_rate = check_success_rate(metrics)
    if success_rate < ALERT_THRESHOLD:
        log_alert(
            f"⚠️  ALERTA: Taxa de sucesso baixa ({success_rate:.1f}% < {ALERT_THRESHOLD}%)",
            "WARNING"
        )
    else:
        log_alert(f"✅ Taxa de sucesso normal: {success_rate:.1f}%", "INFO")
    
    # Verificar tempo de resposta
    avg_time = check_response_time(metrics)
    if avg_time > 0.1:  # > 100ms
        log_alert(
            f"⚠️  ALERTA: Response time elevado ({avg_time*1000:.1f}ms)",
            "WARNING"
        )
    else:
        log_alert(f"✅ Response time normal: {avg_time*1000:.1f}ms", "INFO")
    
    log_alert("Verificação de alertas concluída", "INFO")
    return 0

if __name__ == "__main__":
    sys.exit(main())
