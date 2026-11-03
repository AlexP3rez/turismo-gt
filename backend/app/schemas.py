from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Autenticación (Fase 2) ----------
class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    token_limit: int
    tokens_used: int
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Usuarios (admin) ----------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=72)
    role: Literal["admin", "user"] = "user"
    token_limit: int = Field(20000, ge=0)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    password: Optional[str] = Field(None, min_length=8, max_length=72)
    role: Optional[Literal["admin", "user"]] = None
    token_limit: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


# ---------- Destinos y actividades ----------
class DestinationIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    department: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=50)
    description: str = Field(min_length=20)


class DestinationOut(DestinationIn):
    id: int
    created_at: datetime


class DestinationSaved(DestinationOut):
    indexed: bool  # True si los fragmentos del RAG quedaron actualizados


class ActivityBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: Optional[str] = None
    category: str = Field(min_length=2, max_length=50)
    est_cost_gtq: float = Field(0, ge=0, le=99999999)
    duration_hours: float = Field(2, gt=0, lt=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class ActivityCreate(ActivityBase):
    destination_id: int


class ActivityOut(ActivityBase):
    id: int
    destination_id: int


class ActivitySaved(ActivityOut):
    indexed: bool


class DestinationDetail(DestinationOut):
    activities: list[ActivityOut] = []


# ---------- Servicios de IA ----------
class ServiceOut(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None

# ---------- Chat (Fase 4) ----------
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: Optional[int] = None  # vacío = conversación nueva


class SourceOut(BaseModel):
    id: int
    destination_id: Optional[int] = None
    title: str
    score: float


class UsageOut(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatOut(BaseModel):
    conversation_id: int
    answer: str
    sources: list[SourceOut]
    sufficient_info: bool
    usage: UsageOut
    tokens_remaining: int

# ---------- Agentes (Fase 5) ----------
class AgentIn(BaseModel):
    message: str = Field(min_length=5, max_length=1000)


class AdjustIn(BaseModel):
    plan: str = Field(min_length=20, max_length=8000)    # plan actual (texto)
    change: str = Field(min_length=3, max_length=500)    # cambio de presupuesto o clima


class StepOut(BaseModel):
    step: int
    tool: str
    arguments: dict
    result: str


class AgentOut(BaseModel):
    conversation_id: int
    answer: str
    steps: list[StepOut]
    usage: UsageOut
    tokens_remaining: int