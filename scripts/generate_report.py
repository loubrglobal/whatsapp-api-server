#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

PROJECT_DIR = Path('/home/ubuntu/whatsapp-api-server')
REPORTS_DIR = PROJECT_DIR / 'reports'
BASE_URL = os.getenv('LOCAL_API_BASE_URL', 'http://127.0.0.1:8000')


def request_json(path: str, token: str | None = None) -> dict[str, Any]:
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    response = requests.get(f'{BASE_URL}{path}', headers=headers, timeout=30)
    try:
        payload = response.json()
    except ValueError:
        payload = {'raw': response.text}
    return {'status_code': response.status_code, 'payload': payload}


def safe_bool_label(value: Any) -> str:
    return 'configurado' if value else 'pendente'


def main() -> None:
    load_dotenv(PROJECT_DIR / '.env')
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    token = os.getenv('API_ADMIN_TOKEN')
    now = datetime.now(timezone.utc)

    health = request_json('/health')
    diagnostics = request_json('/diagnostics', token) if token else {'status_code': 0, 'payload': {'error': 'API_ADMIN_TOKEN ausente'}}
    meta_config = request_json('/meta/config', token) if token else {'status_code': 0, 'payload': {'error': 'API_ADMIN_TOKEN ausente'}}
    events = request_json('/events?limit=10', token) if token else {'status_code': 0, 'payload': {'events': []}}
    actions = request_json('/actions?limit=10', token) if token else {'status_code': 0, 'payload': {'actions': []}}

    health_payload = health.get('payload', {})
    configured = health_payload.get('configured', {}) if isinstance(health_payload, dict) else {}
    meta_payload = meta_config.get('payload', {}) if isinstance(meta_config.get('payload'), dict) else {}
    diagnostics_payload = diagnostics.get('payload', {}) if isinstance(diagnostics.get('payload'), dict) else {}
    events_payload = events.get('payload', {}) if isinstance(events.get('payload'), dict) else {}
    actions_payload = actions.get('payload', {}) if isinstance(actions.get('payload'), dict) else {}

    report = {
        'generated_at_utc': now.isoformat(),
        'health_status_code': health.get('status_code'),
        'diagnostics_status_code': diagnostics.get('status_code'),
        'meta_config_status_code': meta_config.get('status_code'),
        'configured': configured,
        'meta_ads_config': meta_payload,
        'diagnostics': diagnostics_payload,
        'recent_events_count': len(events_payload.get('events', [])),
        'recent_actions_count': len(actions_payload.get('actions', [])),
    }

    json_path = REPORTS_DIR / f'operational_report_{now.strftime("%Y%m%d_%H%M%S")}.json'
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    md_path = REPORTS_DIR / 'latest_operational_report.md'
    md_lines = [
        '# Relatório operacional — WhatsApp Cloud API e Meta Ads',
        '',
        f'Gerado em UTC: **{now.isoformat()}**.',
        '',
        '## Saúde do serviço',
        '',
        f'O endpoint local `/health` retornou código **{health.get("status_code")}**.',
        '',
        '| Item | Estado |',
        '|---|---|',
        f'| Token administrativo da API | {safe_bool_label(configured.get("api_admin_token"))} |',
        f'| Token Meta | {safe_bool_label(configured.get("meta_access_token"))} |',
        f'| App Secret Meta | {safe_bool_label(configured.get("meta_app_secret"))} |',
        f'| Verify token webhook | {safe_bool_label(configured.get("verify_token"))} |',
        f'| WABA padrão | {safe_bool_label(configured.get("default_waba_id"))} |',
        f'| Phone Number ID padrão | {safe_bool_label(configured.get("default_phone_number_id"))} |',
        '',
        '## Meta Ads',
        '',
        f'Business IDs configurados: **{len(meta_payload.get("business_ids", [])) if isinstance(meta_payload, dict) else 0}**.',
        '',
        f'Trava de escrita Meta Ads ativa: **{meta_payload.get("write_operations_enabled_by_configuration", False) if isinstance(meta_payload, dict) else False}**.',
        '',
        '## Atividade recente',
        '',
        f'Eventos de webhook recentes consultados: **{report["recent_events_count"]}**.',
        '',
        f'Ações administrativas recentes consultadas: **{report["recent_actions_count"]}**.',
        '',
        '## Observações',
        '',
        'Este relatório é gerado localmente no servidor e não envia mensagens, não registra números e não altera campanhas. Operações reais continuam bloqueadas por configuração e exigem confirmação explícita.',
        '',
    ]
    md_path.write_text('\n'.join(md_lines))
    print(f'generated {json_path} and {md_path}')


if __name__ == '__main__':
    main()
