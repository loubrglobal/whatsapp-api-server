#!/usr/bin/env python3
import os, json, requests
from datetime import datetime
from pathlib import Path

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
WABA_ID = os.getenv("DEFAULT_WABA_ID", "")
PHONE_NUMBER_ID = os.getenv("DEFAULT_PHONE_NUMBER_ID", "")
RECIPIENT_PHONE = os.getenv("ALERT_RECIPIENT_PHONE", "+5511911851815")

GRAPH_API_URL = "https://graph.facebook.com/v23.0"
SEND_MESSAGE_ENDPOINT = f"{GRAPH_API_URL}/{PHONE_NUMBER_ID}/messages"

def send_whatsapp_message(phone, message):
    if not META_ACCESS_TOKEN or not PHONE_NUMBER_ID:
        return {"success": False, "error": "Credenciais não configuradas"}
    
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone.replace("+", "").replace(" ", "").replace("-", ""),
        "type": "text",
        "text": {"body": message}
    }
    
    try:
        response = requests.post(SEND_MESSAGE_ENDPOINT, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return {"success": True, "phone": phone, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"success": False, "error": str(e), "phone": phone}

def send_alert(alert_type, details):
    if alert_type == "low_success_rate":
        message = f"🚨 Taxa de Sucesso: {details.get('success_rate', 'N/A')}% (limite: 95%)"
    elif alert_type == "high_response_time":
        message = f"⚠️ Response Time: {details.get('response_time', 'N/A')}ms (limite: 100ms)"
    elif alert_type == "service_down":
        message = "🔴 CRÍTICO: Serviço Offline!"
    else:
        message = f"ℹ️ {alert_type}: {json.dumps(details)}"
    
    result = send_whatsapp_message(RECIPIENT_PHONE, message)
    
    log_dir = Path("/home/ubuntu/whatsapp-api-server/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "whatsapp_alerts.jsonl", "a") as f:
        f.write(json.dumps({"timestamp": datetime.utcnow().isoformat(), "alert_type": alert_type, "result": result}) + "\n")
    
    return result

if __name__ == "__main__":
    import sys
    alert_type = sys.argv[1] if len(sys.argv) > 1 else "test"
    details = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    result = send_alert(alert_type, details)
    print(json.dumps(result, indent=2))
