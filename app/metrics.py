"""
Módulo de coleta e exposição de métricas de saúde do servidor.
Fornece endpoints para monitoramento em tempo real.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import subprocess

PROJECT_DIR = Path("/home/ubuntu/whatsapp-api-server")
LOGS_DIR = PROJECT_DIR / "logs"
METRICS_FILE = LOGS_DIR / "healthcheck_metrics.json"


class MetricsCollector:
    """Coleta e agrega métricas de saúde do servidor."""

    @staticmethod
    def get_healthcheck_metrics(limit: int = 100) -> Dict[str, Any]:
        """Retorna últimas N métricas de healthcheck."""
        if not METRICS_FILE.exists():
            return {"status": "no_data", "metrics": []}

        try:
            metrics = []
            with open(METRICS_FILE, "r") as f:
                for line in f:
                    try:
                        metrics.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue

            # Retornar últimas N métricas
            recent = metrics[-limit:] if len(metrics) > limit else metrics

            # Calcular estatísticas
            if recent:
                http_codes = [m.get("http_code") for m in recent]
                response_times = [
                    float(m.get("response_time", 0)) for m in recent
                ]

                success_count = sum(1 for code in http_codes if code == 200)
                avg_response_time = (
                    sum(response_times) / len(response_times)
                    if response_times
                    else 0
                )

                return {
                    "status": "ok",
                    "metrics": recent,
                    "stats": {
                        "total": len(recent),
                        "success_count": success_count,
                        "failure_count": len(recent) - success_count,
                        "success_rate": (success_count / len(recent)) * 100,
                        "avg_response_time": round(avg_response_time, 4),
                        "min_response_time": round(min(response_times), 4)
                        if response_times
                        else 0,
                        "max_response_time": round(max(response_times), 4)
                        if response_times
                        else 0,
                    },
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        """Retorna status do serviço systemd."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "whatsapp-api.service"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            is_active = result.returncode == 0

            # Obter tempo de uptime
            uptime_result = subprocess.run(
                [
                    "systemctl",
                    "show",
                    "whatsapp-api.service",
                    "-p",
                    "ActiveEnterTimestamp",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            return {
                "status": "active" if is_active else "inactive",
                "is_active": is_active,
                "uptime_info": uptime_result.stdout.strip(),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_disk_usage() -> Dict[str, Any]:
        """Retorna uso de disco do projeto."""
        try:
            result = subprocess.run(
                ["du", "-sh", str(PROJECT_DIR)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            size = result.stdout.split()[0] if result.stdout else "unknown"

            # Logs
            logs_result = subprocess.run(
                ["du", "-sh", str(LOGS_DIR)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            logs_size = logs_result.stdout.split()[0] if logs_result.stdout else "0"

            return {
                "project_size": size,
                "logs_size": logs_size,
                "status": "ok",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_recent_events(limit: int = 20) -> Dict[str, Any]:
        """Retorna eventos recentes do healthcheck."""
        events_file = LOGS_DIR / "healthcheck_events.log"

        if not events_file.exists():
            return {"status": "no_data", "events": []}

        try:
            with open(events_file, "r") as f:
                lines = f.readlines()

            # Últimos N eventos
            recent_lines = lines[-limit:] if len(lines) > limit else lines

            events = []
            for line in recent_lines:
                line = line.strip()
                if line:
                    events.append({"raw": line})

            return {"status": "ok", "events": events}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_all_metrics() -> Dict[str, Any]:
        """Retorna todas as métricas agregadas."""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "healthcheck": MetricsCollector.get_healthcheck_metrics(limit=50),
            "service": MetricsCollector.get_service_status(),
            "disk": MetricsCollector.get_disk_usage(),
            "recent_events": MetricsCollector.get_recent_events(limit=10),
        }
