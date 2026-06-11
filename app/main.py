import hashlib
import hmac
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.meta_ads import (
    CampaignCreateRequest,
    CampaignStatusUpdateRequest,
    GenericMetaWriteRequest,
    MetaAdsInsightsQuery,
    MetaAdsReadQuery,
    campaign_templates,
    create_campaign,
    diagnose_ad_account,
    diagnose_configured_assets,
    execute_generic_meta_write,
    get_ad,
    get_ad_account,
    get_adset,
    get_campaign,
    get_configured_portfolios,
    get_insights,
    list_ads,
    list_adsets,
    list_business_ad_accounts,
    list_campaigns,
    preview_campaign_create,
    preview_campaign_status_update,
    preview_generic_meta_write,
    update_campaign_status,
)

load_dotenv()

APP_NAME = "WhatsApp Meta API Server"
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v23.0")
GRAPH_BASE_URL = os.getenv("META_GRAPH_BASE_URL", f"https://graph.facebook.com/{GRAPH_VERSION}")
DATABASE_PATH = os.getenv("DATABASE_PATH", "/home/ubuntu/whatsapp-api-server/data/whatsapp_api.sqlite3")
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "change-me-verify-token")
APP_SECRET = os.getenv("META_APP_SECRET", "")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
DEFAULT_WABA_ID = os.getenv("DEFAULT_WABA_ID", "")
DEFAULT_PHONE_NUMBER_ID = os.getenv("DEFAULT_PHONE_NUMBER_ID", "")
API_ADMIN_TOKEN = os.getenv("API_ADMIN_TOKEN", "")

app = FastAPI(title=APP_NAME, version="0.1.0")


class TextMessageRequest(BaseModel):
    to: str = Field(..., description="Número do destinatário em formato internacional, apenas dígitos.")
    body: str = Field(..., min_length=1, max_length=4096)
    phone_number_id: Optional[str] = None


class RegisterNumberRequest(BaseModel):
    phone_number_id: str
    pin: str = Field(..., min_length=6, max_length=6)


class TemplateMessageRequest(BaseModel):
    to: str
    template_name: str
    language_code: str = "pt_BR"
    phone_number_id: Optional[str] = None
    components: Optional[list[dict[str, Any]]] = None


class WebhookTestRequest(BaseModel):
    payload: Dict[str, Any]


@contextmanager
def db_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at INTEGER NOT NULL,
                event_type TEXT,
                waba_id TEXT,
                phone_number_id TEXT,
                from_wa_id TEXT,
                message_id TEXT,
                payload TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at INTEGER NOT NULL,
                action TEXT NOT NULL,
                target TEXT,
                request_payload TEXT,
                response_status INTEGER,
                response_payload TEXT
            )
            """
        )


def require_admin(authorization: Optional[str] = Header(default=None)) -> None:
    if not API_ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="API_ADMIN_TOKEN ainda não foi configurado no servidor.")
    expected = f"Bearer {API_ADMIN_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token administrativo inválido ou ausente.")


def graph_headers() -> dict[str, str]:
    if not ACCESS_TOKEN:
        raise HTTPException(status_code=503, detail="META_ACCESS_TOKEN ainda não foi configurado no servidor.")
    return {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}


def graph_request(method: str, path: str, payload: Optional[dict[str, Any]] = None, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    url = f"{GRAPH_BASE_URL}/{path.lstrip('/')}"
    try:
        response = requests.request(method, url, headers=graph_headers(), json=payload, params=params, timeout=30)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Falha de comunicação com a Graph API: {exc}") from exc

    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text}

    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO api_actions (created_at, action, target, request_payload, response_status, response_payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(time.time()), method.upper(), path, json.dumps(payload or params or {}, ensure_ascii=False), response.status_code, json.dumps(data, ensure_ascii=False)),
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=data)
    return data


def verify_meta_signature(raw_body: bytes, signature_header: Optional[str]) -> None:
    if not APP_SECRET:
        return
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Assinatura X-Hub-Signature-256 ausente.")
    expected = "sha256=" + hmac.new(APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=403, detail="Assinatura do webhook inválida.")


def extract_event_summary(payload: dict[str, Any]) -> dict[str, Optional[str]]:
    summary: dict[str, Optional[str]] = {
        "event_type": None,
        "waba_id": None,
        "phone_number_id": None,
        "from_wa_id": None,
        "message_id": None,
    }
    try:
        entry = (payload.get("entry") or [{}])[0]
        summary["waba_id"] = str(entry.get("id")) if entry.get("id") else None
        change = (entry.get("changes") or [{}])[0]
        summary["event_type"] = change.get("field")
        value = change.get("value") or {}
        metadata = value.get("metadata") or {}
        summary["phone_number_id"] = str(metadata.get("phone_number_id")) if metadata.get("phone_number_id") else None
        messages = value.get("messages") or []
        statuses = value.get("statuses") or []
        if messages:
            summary["from_wa_id"] = str(messages[0].get("from")) if messages[0].get("from") else None
            summary["message_id"] = str(messages[0].get("id")) if messages[0].get("id") else None
        elif statuses:
            summary["from_wa_id"] = str(statuses[0].get("recipient_id")) if statuses[0].get("recipient_id") else None
            summary["message_id"] = str(statuses[0].get("id")) if statuses[0].get("id") else None
    except Exception:
        pass
    return summary


def store_webhook_event(payload: dict[str, Any]) -> dict[str, Optional[str]]:
    summary = extract_event_summary(payload)
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO webhook_events (received_at, event_type, waba_id, phone_number_id, from_wa_id, message_id, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(time.time()),
                summary.get("event_type"),
                summary.get("waba_id"),
                summary.get("phone_number_id"),
                summary.get("from_wa_id"),
                summary.get("message_id"),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
    return summary


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": APP_NAME,
        "graph_version": GRAPH_VERSION,
        "configured": {
            "meta_access_token": bool(ACCESS_TOKEN),
            "meta_app_secret": bool(APP_SECRET),
            "verify_token": VERIFY_TOKEN != "change-me-verify-token",
            "default_waba_id": bool(DEFAULT_WABA_ID),
            "default_phone_number_id": bool(DEFAULT_PHONE_NUMBER_ID),
            "api_admin_token": bool(API_ADMIN_TOKEN),
        },
    }


@app.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(request: Request) -> str:
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        return challenge
    raise HTTPException(status_code=403, detail="Verificação do webhook recusada.")


@app.post("/webhook")
async def receive_webhook(request: Request, x_hub_signature_256: Optional[str] = Header(default=None)) -> dict[str, Any]:
    raw_body = await request.body()
    verify_meta_signature(raw_body, x_hub_signature_256)
    payload = json.loads(raw_body.decode("utf-8"))
    summary = store_webhook_event(payload)
    return {"received": True, "summary": summary}


@app.post("/webhook/test", dependencies=[Depends(require_admin)])
def webhook_test(body: WebhookTestRequest) -> dict[str, Any]:
    summary = store_webhook_event(body.payload)
    return {"stored": True, "summary": summary}


@app.get("/events", dependencies=[Depends(require_admin)])
def list_events(limit: int = 50) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 200))
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, received_at, event_type, waba_id, phone_number_id, from_wa_id, message_id, payload
            FROM webhook_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    events = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        events.append(item)
    return {"events": events}


@app.get("/actions", dependencies=[Depends(require_admin)])
def list_actions(limit: int = 50) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 200))
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, action, target, request_payload, response_status, response_payload
            FROM api_actions
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    actions = []
    for row in rows:
        item = dict(row)
        item["request_payload"] = json.loads(item["request_payload"] or "{}")
        item["response_payload"] = json.loads(item["response_payload"] or "{}")
        actions.append(item)
    return {"actions": actions}


@app.get("/waba/{waba_id}/phone-numbers", dependencies=[Depends(require_admin)])
def get_phone_numbers(waba_id: str) -> dict[str, Any]:
    return graph_request("GET", f"/{waba_id}/phone_numbers", params={"fields": "id,display_phone_number,verified_name,quality_rating,code_verification_status,platform_type,throughput"})


@app.get("/phone-number/{phone_number_id}", dependencies=[Depends(require_admin)])
def get_phone_number(phone_number_id: str) -> dict[str, Any]:
    fields = "id,display_phone_number,verified_name,quality_rating,code_verification_status,platform_type,throughput,certificate"
    return graph_request("GET", f"/{phone_number_id}", params={"fields": fields})


@app.post("/phone-number/register", dependencies=[Depends(require_admin)])
def register_number(body: RegisterNumberRequest) -> dict[str, Any]:
    payload = {"messaging_product": "whatsapp", "pin": body.pin}
    return graph_request("POST", f"/{body.phone_number_id}/register", payload=payload)


@app.post("/messages/text", dependencies=[Depends(require_admin)])
def send_text_message(body: TextMessageRequest) -> dict[str, Any]:
    phone_number_id = body.phone_number_id or DEFAULT_PHONE_NUMBER_ID
    if not phone_number_id:
        raise HTTPException(status_code=400, detail="Informe phone_number_id ou configure DEFAULT_PHONE_NUMBER_ID.")
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": body.to,
        "type": "text",
        "text": {"preview_url": False, "body": body.body},
    }
    return graph_request("POST", f"/{phone_number_id}/messages", payload=payload)


@app.post("/messages/template", dependencies=[Depends(require_admin)])
def send_template_message(body: TemplateMessageRequest) -> dict[str, Any]:
    phone_number_id = body.phone_number_id or DEFAULT_PHONE_NUMBER_ID
    if not phone_number_id:
        raise HTTPException(status_code=400, detail="Informe phone_number_id ou configure DEFAULT_PHONE_NUMBER_ID.")
    template: dict[str, Any] = {"name": body.template_name, "language": {"code": body.language_code}}
    if body.components:
        template["components"] = body.components
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": body.to,
        "type": "template",
        "template": template,
    }
    return graph_request("POST", f"/{phone_number_id}/messages", payload=payload)


@app.get("/waba/{waba_id}/message-templates", dependencies=[Depends(require_admin)])
def get_templates(waba_id: str) -> dict[str, Any]:
    return graph_request("GET", f"/{waba_id}/message_templates", params={"fields": "id,name,status,category,language,quality_score,components"})


@app.get("/meta/config", dependencies=[Depends(require_admin)])
def meta_ads_config() -> dict[str, Any]:
    """Lista IDs Meta Ads configurados localmente sem expor credenciais."""
    return get_configured_portfolios()


@app.get("/meta/campaign-templates", dependencies=[Depends(require_admin)])
def meta_ads_campaign_templates() -> dict[str, Any]:
    """Lista modelos técnicos de campanha e o estado das travas de escrita."""
    return campaign_templates()


@app.get("/meta/business/{business_id}/ad-accounts", dependencies=[Depends(require_admin)])
def meta_ads_business_ad_accounts(business_id: str, query: MetaAdsReadQuery = Depends()) -> dict[str, Any]:
    """Lista contas de anúncios pertencentes a um portfólio/Business Manager."""
    return list_business_ad_accounts(graph_request, business_id, query)


@app.get("/meta/ad-account/{ad_account_id}", dependencies=[Depends(require_admin)])
def meta_ads_ad_account(ad_account_id: str, fields: Optional[str] = None) -> dict[str, Any]:
    """Consulta dados cadastrais, moeda, status e possíveis restrições de uma conta de anúncios."""
    return get_ad_account(graph_request, ad_account_id, fields=fields)


@app.get("/meta/ad-account/{ad_account_id}/campaigns", dependencies=[Depends(require_admin)])
def meta_ads_campaigns(ad_account_id: str, query: MetaAdsReadQuery = Depends()) -> dict[str, Any]:
    """Lista campanhas de uma conta de anúncios com status, orçamento e campos de alerta."""
    return list_campaigns(graph_request, ad_account_id, query)


@app.get("/meta/ad-account/{ad_account_id}/adsets", dependencies=[Depends(require_admin)])
def meta_ads_adsets(ad_account_id: str, query: MetaAdsReadQuery = Depends()) -> dict[str, Any]:
    """Lista conjuntos de anúncios de uma conta de anúncios."""
    return list_adsets(graph_request, ad_account_id, query)


@app.get("/meta/ad-account/{ad_account_id}/ads", dependencies=[Depends(require_admin)])
def meta_ads_ads(ad_account_id: str, query: MetaAdsReadQuery = Depends()) -> dict[str, Any]:
    """Lista anúncios individuais de uma conta de anúncios."""
    return list_ads(graph_request, ad_account_id, query)


@app.get("/meta/ad-account/{ad_account_id}/insights", dependencies=[Depends(require_admin)])
def meta_ads_insights(ad_account_id: str, query: MetaAdsInsightsQuery = Depends()) -> dict[str, Any]:
    """Obtém métricas brutas da Graph API para relatório; os nomes exibidos devem ser normalizados em relatórios finais."""
    return get_insights(graph_request, ad_account_id, query)


@app.get("/meta/campaign/{campaign_id}", dependencies=[Depends(require_admin)])
def meta_ads_campaign(campaign_id: str, fields: Optional[str] = None) -> dict[str, Any]:
    """Consulta uma campanha específica, preservando o escopo correto do ativo consultado."""
    return get_campaign(graph_request, campaign_id, fields=fields)


@app.get("/meta/adset/{adset_id}", dependencies=[Depends(require_admin)])
def meta_ads_adset(adset_id: str, fields: Optional[str] = None) -> dict[str, Any]:
    """Consulta um conjunto de anúncios específico."""
    return get_adset(graph_request, adset_id, fields=fields)


@app.get("/meta/ad/{ad_id}", dependencies=[Depends(require_admin)])
def meta_ads_ad(ad_id: str, fields: Optional[str] = None) -> dict[str, Any]:
    """Consulta um anúncio específico."""
    return get_ad(graph_request, ad_id, fields=fields)


@app.get("/meta/ad-account/{ad_account_id}/diagnostics", dependencies=[Depends(require_admin)])
def meta_ads_ad_account_diagnostics(ad_account_id: str, include_campaigns: bool = True) -> dict[str, Any]:
    """Executa diagnóstico técnico de uma conta de anúncios e sinaliza restrições ou recomendações retornadas pela API."""
    return diagnose_ad_account(graph_request, ad_account_id, include_campaigns=include_campaigns)


@app.get("/meta/diagnostics", dependencies=[Depends(require_admin)])
def meta_ads_configured_diagnostics() -> dict[str, Any]:
    """Executa diagnóstico dos Business IDs e contas de anúncios configurados no .env."""
    return diagnose_configured_assets(graph_request)


@app.post("/meta/ad-account/{ad_account_id}/campaigns/preview", dependencies=[Depends(require_admin)])
def meta_ads_campaign_create_preview(ad_account_id: str, body: CampaignCreateRequest) -> dict[str, Any]:
    """Pré-visualiza o payload de criação de campanha sem executar alteração real."""
    return preview_campaign_create(ad_account_id, body)


@app.post("/meta/ad-account/{ad_account_id}/campaigns/create", dependencies=[Depends(require_admin)])
def meta_ads_campaign_create(ad_account_id: str, body: CampaignCreateRequest) -> dict[str, Any]:
    """Cria campanha apenas se a trava global e o texto de confirmação explícita estiverem corretos."""
    return create_campaign(graph_request, ad_account_id, body)


@app.post("/meta/campaign/{campaign_id}/status/preview", dependencies=[Depends(require_admin)])
def meta_ads_campaign_status_preview(campaign_id: str, body: CampaignStatusUpdateRequest) -> dict[str, Any]:
    """Pré-visualiza alteração de status de campanha sem executar alteração real."""
    return preview_campaign_status_update(campaign_id, body)


@app.post("/meta/campaign/{campaign_id}/status", dependencies=[Depends(require_admin)])
def meta_ads_campaign_status_update(campaign_id: str, body: CampaignStatusUpdateRequest) -> dict[str, Any]:
    """Altera status de campanha apenas se a trava global e o texto de confirmação explícita estiverem corretos."""
    return update_campaign_status(graph_request, campaign_id, body)


@app.post("/meta/write-preview/{path:path}", dependencies=[Depends(require_admin)])
def meta_ads_generic_write_preview(path: str, body: GenericMetaWriteRequest) -> dict[str, Any]:
    """Pré-visualiza uma operação técnica POST genérica na Graph API sem executar alteração real."""
    return preview_generic_meta_write(f"/{path}", body)


@app.post("/meta/write/{path:path}", dependencies=[Depends(require_admin)])
def meta_ads_generic_write(path: str, body: GenericMetaWriteRequest) -> dict[str, Any]:
    """Executa POST técnico genérico apenas após trava global e confirmação explícita."""
    return execute_generic_meta_write(graph_request, f"/{path}", body)


@app.get("/diagnostics", dependencies=[Depends(require_admin)])
def diagnostics() -> dict[str, Any]:
    result: dict[str, Any] = {"health": health(), "meta_ads_config": get_configured_portfolios()}
    if DEFAULT_WABA_ID and ACCESS_TOKEN:
        try:
            result["default_waba_phone_numbers"] = graph_request("GET", f"/{DEFAULT_WABA_ID}/phone_numbers", params={"fields": "id,display_phone_number,verified_name,quality_rating,code_verification_status,platform_type"})
        except HTTPException as exc:
            result["default_waba_phone_numbers_error"] = exc.detail
    if DEFAULT_PHONE_NUMBER_ID and ACCESS_TOKEN:
        try:
            result["default_phone_number"] = graph_request("GET", f"/{DEFAULT_PHONE_NUMBER_ID}", params={"fields": "id,display_phone_number,verified_name,quality_rating,code_verification_status,platform_type"})
        except HTTPException as exc:
            result["default_phone_number_error"] = exc.detail
    if ACCESS_TOKEN:
        try:
            result["meta_ads_configured_diagnostics"] = diagnose_configured_assets(graph_request)
        except HTTPException as exc:
            result["meta_ads_configured_diagnostics_error"] = exc.detail
    return result

# ============================================================================
# Endpoints de Métricas e Monitoramento
# ============================================================================

from app.metrics import MetricsCollector

@app.get("/metrics/health", tags=["Monitoring"])
async def get_health_metrics():
    """Retorna métricas de healthcheck dos últimos 50 testes."""
    return MetricsCollector.get_healthcheck_metrics(limit=50)

@app.get("/metrics/service", tags=["Monitoring"])
async def get_service_metrics():
    """Retorna status do serviço systemd."""
    return MetricsCollector.get_service_status()

@app.get("/metrics/disk", tags=["Monitoring"])
async def get_disk_metrics():
    """Retorna uso de disco do projeto."""
    return MetricsCollector.get_disk_usage()

@app.get("/metrics/events", tags=["Monitoring"])
async def get_recent_events(limit: int = 20):
    """Retorna eventos recentes do healthcheck."""
    return MetricsCollector.get_recent_events(limit=limit)

@app.get("/metrics/all", tags=["Monitoring"])
async def get_all_metrics():
    """Retorna todas as métricas agregadas em tempo real."""
    return MetricsCollector.get_all_metrics()
