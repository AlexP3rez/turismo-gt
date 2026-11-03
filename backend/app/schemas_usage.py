from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------- Historial ----------
class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[list] = None   # fuentes del RAG
    steps: Optional[list] = None     # pasos de los agentes
    created_at: datetime


class ConversationOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    service_code: str
    service_name: str
    title: Optional[str] = None
    created_at: datetime
    message_count: int
    total_tokens: int


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


# ---------- Consumo ----------
class ServiceUsageOut(BaseModel):
    service_code: str
    service_name: str
    queries: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class MyUsageOut(BaseModel):
    token_limit: int
    tokens_used: int        # contador que bloquea al usuario (el admin puede reiniciarlo)
    tokens_remaining: int
    total_queries: int      # suma del historial (usage_log) con los filtros aplicados
    total_tokens: int
    by_service: list[ServiceUsageOut]


class UsageRecordOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    service_code: str
    service_name: str
    conversation_id: Optional[int] = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime


# ---------- Reporte (web y Power BI) ----------
class ReportRow(BaseModel):
    day: date
    service_code: str
    service_name: str
    user_id: int
    user_email: str
    queries: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


# ---------- API keys ----------
class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class ApiKeyOut(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    api_key: str   # solo se muestra al crearla