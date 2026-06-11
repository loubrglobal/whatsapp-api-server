import os
from typing import Any, Callable, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

GraphRequest = Callable[[str, str, Optional[dict[str, Any]], Optional[dict[str, Any]]], dict[str, Any]]

DEFAULT_META_BUSINESS_IDS = [
    item.strip()
    for item in os.getenv("DEFAULT_META_BUSINESS_IDS", "").split(",")
    if item.strip()
]
DEFAULT_AD_ACCOUNT_IDS = [
    item.strip()
    for item in os.getenv("DEFAULT_AD_ACCOUNT_IDS", "").split(",")
    if item.strip()
]

AD_ACCOUNT_DEFAULT_FIELDS = ",".join(
    [
        "id",
        "account_id",
        "name",
        "currency",
        "timezone_name",
        "account_status",
        "disable_reason",
        "business",
        "amount_spent",
        "balance",
        "spend_cap",
        "min_daily_budget",
        "capabilities",
        "is_prepay_account",
        "created_time",
    ]
)

CAMPAIGN_DEFAULT_FIELDS = ",".join(
    [
        "id",
        "name",
        "objective",
        "status",
        "effective_status",
        "configured_status",
        "buying_type",
        "special_ad_categories",
        "daily_budget",
        "lifetime_budget",
        "budget_remaining",
        "start_time",
        "stop_time",
        "created_time",
        "updated_time",
        "issues_info",
        "recommendations",
    ]
)

ADSET_DEFAULT_FIELDS = ",".join(
    [
        "id",
        "name",
        "campaign_id",
        "status",
        "effective_status",
        "configured_status",
        "optimization_goal",
        "billing_event",
        "daily_budget",
        "lifetime_budget",
        "budget_remaining",
        "bid_strategy",
        "start_time",
        "end_time",
        "created_time",
        "updated_time",
        "issues_info",
        "recommendations",
    ]
)

AD_DEFAULT_FIELDS = ",".join(
    [
        "id",
        "name",
        "campaign_id",
        "adset_id",
        "status",
        "effective_status",
        "configured_status",
        "created_time",
        "updated_time",
        "issues_info",
        "recommendations",
        "creative{id,name,object_story_spec,thumbnail_url}",
    ]
)

INSIGHTS_DEFAULT_FIELDS = ",".join(
    [
        "campaign_id",
        "campaign_name",
        "adset_id",
        "adset_name",
        "ad_id",
        "ad_name",
        "date_start",
        "date_stop",
        "objective",
        "spend",
        "impressions",
        "reach",
        "frequency",
        "cpm",
        "cpc",
        "clicks",
        "inline_link_clicks",
        "actions",
        "cost_per_action_type",
        "purchase_roas",
    ]
)


class MetaAdsReadQuery(BaseModel):
    fields: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=500)
    after: Optional[str] = None


class MetaAdsInsightsQuery(BaseModel):
    level: str = Field(default="campaign", pattern="^(account|campaign|adset|ad)$")
    date_preset: str = "last_30d"
    time_increment: Optional[str] = None
    fields: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=500)
    after: Optional[str] = None


def normalize_ad_account_id(ad_account_id: str) -> str:
    cleaned = ad_account_id.strip()
    if cleaned.startswith("act_"):
        return cleaned
    return f"act_{cleaned}"


def _params(fields: str, limit: int = 100, after: Optional[str] = None, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    params: dict[str, Any] = {"fields": fields, "limit": limit}
    if after:
        params["after"] = after
    if extra:
        params.update({key: value for key, value in extra.items() if value is not None})
    return params


def get_configured_portfolios() -> dict[str, Any]:
    return {
        "business_ids": DEFAULT_META_BUSINESS_IDS,
        "ad_account_ids": [normalize_ad_account_id(item) for item in DEFAULT_AD_ACCOUNT_IDS],
        "write_operations_enabled_by_configuration": os.getenv("META_ADS_WRITE_ENABLED", "false").lower() == "true",
    }


def list_business_ad_accounts(graph_request: GraphRequest, business_id: str, query: MetaAdsReadQuery) -> dict[str, Any]:
    fields = query.fields or AD_ACCOUNT_DEFAULT_FIELDS
    return graph_request("GET", f"/{business_id}/owned_ad_accounts", None, _params(fields, query.limit, query.after))


def get_ad_account(graph_request: GraphRequest, ad_account_id: str, fields: Optional[str] = None) -> dict[str, Any]:
    return graph_request("GET", f"/{normalize_ad_account_id(ad_account_id)}", None, {"fields": fields or AD_ACCOUNT_DEFAULT_FIELDS})


def list_campaigns(graph_request: GraphRequest, ad_account_id: str, query: MetaAdsReadQuery) -> dict[str, Any]:
    fields = query.fields or CAMPAIGN_DEFAULT_FIELDS
    return graph_request("GET", f"/{normalize_ad_account_id(ad_account_id)}/campaigns", None, _params(fields, query.limit, query.after))


def list_adsets(graph_request: GraphRequest, ad_account_id: str, query: MetaAdsReadQuery) -> dict[str, Any]:
    fields = query.fields or ADSET_DEFAULT_FIELDS
    return graph_request("GET", f"/{normalize_ad_account_id(ad_account_id)}/adsets", None, _params(fields, query.limit, query.after))


def list_ads(graph_request: GraphRequest, ad_account_id: str, query: MetaAdsReadQuery) -> dict[str, Any]:
    fields = query.fields or AD_DEFAULT_FIELDS
    return graph_request("GET", f"/{normalize_ad_account_id(ad_account_id)}/ads", None, _params(fields, query.limit, query.after))


def get_campaign(graph_request: GraphRequest, campaign_id: str, fields: Optional[str] = None) -> dict[str, Any]:
    return graph_request("GET", f"/{campaign_id}", None, {"fields": fields or CAMPAIGN_DEFAULT_FIELDS})


def get_adset(graph_request: GraphRequest, adset_id: str, fields: Optional[str] = None) -> dict[str, Any]:
    return graph_request("GET", f"/{adset_id}", None, {"fields": fields or ADSET_DEFAULT_FIELDS})


def get_ad(graph_request: GraphRequest, ad_id: str, fields: Optional[str] = None) -> dict[str, Any]:
    return graph_request("GET", f"/{ad_id}", None, {"fields": fields or AD_DEFAULT_FIELDS})


def get_insights(graph_request: GraphRequest, ad_account_id: str, query: MetaAdsInsightsQuery) -> dict[str, Any]:
    fields = query.fields or INSIGHTS_DEFAULT_FIELDS
    params = _params(
        fields,
        query.limit,
        query.after,
        {"level": query.level, "date_preset": query.date_preset, "time_increment": query.time_increment},
    )
    return graph_request("GET", f"/{normalize_ad_account_id(ad_account_id)}/insights", None, params)


def diagnose_ad_account(graph_request: GraphRequest, ad_account_id: str, include_campaigns: bool = True) -> dict[str, Any]:
    account = get_ad_account(graph_request, ad_account_id)
    diagnosis: dict[str, Any] = {
        "ad_account": account,
        "warnings": [],
        "campaigns": None,
    }
    account_status = account.get("account_status")
    disable_reason = account.get("disable_reason")
    if account_status not in (None, 1):
        diagnosis["warnings"].append(
            {
                "scope": "ad_account",
                "code": "account_status_not_active",
                "message": "A conta de anúncios não retornou status ativo pela Graph API.",
                "account_status": account_status,
            }
        )
    if disable_reason not in (None, 0):
        diagnosis["warnings"].append(
            {
                "scope": "ad_account",
                "code": "disable_reason_present",
                "message": "A conta de anúncios retornou motivo de desativação/restrição.",
                "disable_reason": disable_reason,
            }
        )
    if include_campaigns:
        try:
            campaigns = list_campaigns(graph_request, ad_account_id, MetaAdsReadQuery(limit=100))
            diagnosis["campaigns"] = campaigns
            for campaign in campaigns.get("data", []):
                if campaign.get("issues_info") or campaign.get("recommendations"):
                    diagnosis["warnings"].append(
                        {
                            "scope": "campaign",
                            "campaign_id": campaign.get("id"),
                            "campaign_name": campaign.get("name"),
                            "code": "campaign_issues_or_recommendations",
                            "issues_info": campaign.get("issues_info"),
                            "recommendations": campaign.get("recommendations"),
                        }
                    )
        except HTTPException as exc:
            diagnosis["campaigns_error"] = exc.detail
    return diagnosis


def diagnose_configured_assets(graph_request: GraphRequest) -> dict[str, Any]:
    configured = get_configured_portfolios()
    result: dict[str, Any] = {"configured": configured, "businesses": [], "ad_accounts": []}
    for business_id in configured["business_ids"]:
        item: dict[str, Any] = {"business_id": business_id}
        try:
            item["owned_ad_accounts"] = list_business_ad_accounts(graph_request, business_id, MetaAdsReadQuery(limit=100))
        except HTTPException as exc:
            item["error"] = exc.detail
        result["businesses"].append(item)
    for ad_account_id in configured["ad_account_ids"]:
        item = {"ad_account_id": ad_account_id}
        try:
            item["diagnosis"] = diagnose_ad_account(graph_request, ad_account_id, include_campaigns=False)
        except HTTPException as exc:
            item["error"] = exc.detail
        result["ad_accounts"].append(item)
    return result


META_ADS_WRITE_CONFIRMATION_PHRASE = os.getenv("META_ADS_WRITE_CONFIRMATION_PHRASE", "CONFIRMO ALTERAR META ADS")


class CampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=400)
    objective: str = Field(..., min_length=1, max_length=80)
    status: str = Field(default="PAUSED", pattern="^(PAUSED|ACTIVE)$")
    special_ad_categories: list[str] = Field(default_factory=lambda: ["NONE"])
    buying_type: str = "AUCTION"
    daily_budget: Optional[int] = Field(default=None, ge=1)
    lifetime_budget: Optional[int] = Field(default=None, ge=1)
    bid_strategy: Optional[str] = None
    start_time: Optional[str] = None
    stop_time: Optional[str] = None
    confirmation_text: Optional[str] = None


class CampaignStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(ACTIVE|PAUSED|DELETED|ARCHIVED)$")
    confirmation_text: Optional[str] = None


class GenericMetaWriteRequest(BaseModel):
    payload: dict[str, Any]
    confirmation_text: Optional[str] = None


def meta_ads_write_enabled() -> bool:
    return os.getenv("META_ADS_WRITE_ENABLED", "false").lower() == "true"


def assert_write_authorized(confirmation_text: Optional[str]) -> None:
    if not meta_ads_write_enabled():
        raise HTTPException(
            status_code=403,
            detail={
                "blocked": True,
                "reason": "META_ADS_WRITE_ENABLED está false no servidor.",
                "required_action": "Ativar a trava apenas depois de confirmação explícita do usuário.",
            },
        )
    if confirmation_text != META_ADS_WRITE_CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=403,
            detail={
                "blocked": True,
                "reason": "Texto de confirmação ausente ou inválido.",
                "required_confirmation_text": META_ADS_WRITE_CONFIRMATION_PHRASE,
            },
        )


def campaign_templates() -> dict[str, Any]:
    return {
        "safety": {
            "write_enabled": meta_ads_write_enabled(),
            "required_confirmation_text": META_ADS_WRITE_CONFIRMATION_PHRASE,
            "default_created_status": "PAUSED",
            "note": "As rotas de escrita permanecem bloqueadas até confirmação explícita e ativação da trava no .env.",
        },
        "templates": [
            {
                "name": "Campanha pausada para mensagens WhatsApp",
                "objective": "OUTCOME_ENGAGEMENT",
                "status": "PAUSED",
                "special_ad_categories": ["NONE"],
                "buying_type": "AUCTION",
                "daily_budget": 5000,
                "notes": "Exemplo em unidade mínima da moeda da conta; revisar objetivo, destino, criativo e conjunto antes de publicar.",
            },
            {
                "name": "Campanha pausada para vendas",
                "objective": "OUTCOME_SALES",
                "status": "PAUSED",
                "special_ad_categories": ["NONE"],
                "buying_type": "AUCTION",
                "daily_budget": 10000,
                "notes": "Modelo técnico inicial; não cria conjunto, anúncio ou criativo sem payload complementar aprovado.",
            },
        ],
    }


def build_campaign_payload(body: CampaignCreateRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": body.name,
        "objective": body.objective,
        "status": body.status,
        "special_ad_categories": body.special_ad_categories,
        "buying_type": body.buying_type,
    }
    optional_values = {
        "daily_budget": body.daily_budget,
        "lifetime_budget": body.lifetime_budget,
        "bid_strategy": body.bid_strategy,
        "start_time": body.start_time,
        "stop_time": body.stop_time,
    }
    payload.update({key: value for key, value in optional_values.items() if value is not None})
    return payload


def preview_campaign_create(ad_account_id: str, body: CampaignCreateRequest) -> dict[str, Any]:
    return {
        "will_execute": False,
        "target": f"/{normalize_ad_account_id(ad_account_id)}/campaigns",
        "method": "POST",
        "payload": build_campaign_payload(body),
        "safety": {
            "write_enabled": meta_ads_write_enabled(),
            "required_confirmation_text": META_ADS_WRITE_CONFIRMATION_PHRASE,
            "provided_confirmation_matches": body.confirmation_text == META_ADS_WRITE_CONFIRMATION_PHRASE,
        },
    }


def create_campaign(graph_request: GraphRequest, ad_account_id: str, body: CampaignCreateRequest) -> dict[str, Any]:
    assert_write_authorized(body.confirmation_text)
    return graph_request("POST", f"/{normalize_ad_account_id(ad_account_id)}/campaigns", build_campaign_payload(body), None)


def preview_campaign_status_update(campaign_id: str, body: CampaignStatusUpdateRequest) -> dict[str, Any]:
    return {
        "will_execute": False,
        "target": f"/{campaign_id}",
        "method": "POST",
        "payload": {"status": body.status},
        "safety": {
            "write_enabled": meta_ads_write_enabled(),
            "required_confirmation_text": META_ADS_WRITE_CONFIRMATION_PHRASE,
            "provided_confirmation_matches": body.confirmation_text == META_ADS_WRITE_CONFIRMATION_PHRASE,
        },
    }


def update_campaign_status(graph_request: GraphRequest, campaign_id: str, body: CampaignStatusUpdateRequest) -> dict[str, Any]:
    assert_write_authorized(body.confirmation_text)
    return graph_request("POST", f"/{campaign_id}", {"status": body.status}, None)


def preview_generic_meta_write(path: str, body: GenericMetaWriteRequest) -> dict[str, Any]:
    return {
        "will_execute": False,
        "target": path,
        "method": "POST",
        "payload": body.payload,
        "safety": {
            "write_enabled": meta_ads_write_enabled(),
            "required_confirmation_text": META_ADS_WRITE_CONFIRMATION_PHRASE,
            "provided_confirmation_matches": body.confirmation_text == META_ADS_WRITE_CONFIRMATION_PHRASE,
        },
    }


def execute_generic_meta_write(graph_request: GraphRequest, path: str, body: GenericMetaWriteRequest) -> dict[str, Any]:
    assert_write_authorized(body.confirmation_text)
    return graph_request("POST", path, body.payload, None)
