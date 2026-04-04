from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class OnboardingRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    goal: str = Field(min_length=2, max_length=50)
    experience: str = Field(min_length=2, max_length=50)
    risk: str = Field(min_length=2, max_length=50)
    asset: str = Field(min_length=2, max_length=50)


class PolicyItem(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    value: str = Field(min_length=1, max_length=255)
    enabled: bool = True


class PolicySelectionRequest(BaseModel):
    email: EmailStr
    policies: list[PolicyItem] = Field(default_factory=list, max_length=20)


class TradeIntent(BaseModel):
    user_email: EmailStr
    ticker: str = Field(min_length=1, max_length=20)
    side: str
    notional_usd: float = Field(gt=0, le=1_000_000)
    quantity: float | None = Field(default=None, gt=0)
    reason: str = Field(min_length=3, max_length=500)
    source: str = Field(default='frontend', min_length=2, max_length=50)
    asset_class: str = Field(default='equity', min_length=2, max_length=50)
    mode: str = Field(default='paper', min_length=2, max_length=20)

    @field_validator('side')
    @classmethod
    def validate_side(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {'buy', 'sell'}:
            raise ValueError('side must be buy or sell')
        return normalized


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    email: EmailStr | None = None


class ArmoriqRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    email: EmailStr | None = None
    auto_execute: bool = False


class AgentConfigRequest(BaseModel):
    user_email: EmailStr | None = None
    tickers: list[str] = Field(default_factory=list, max_length=10)
    loop_interval_seconds: int | None = Field(default=None, ge=10, le=3600)


class IntentDecisionOut(BaseModel):
    allowed: bool
    decision: str
    rule_id: str
    rationale: str
    evaluated_at: datetime | str


class TradeOut(BaseModel):
    id: int
    asset: str
    trade_type: str
    amount: float
    pnl_percent: float
    status: str
    auto_ai: bool
    execution_reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArmoriqActionOut(BaseModel):
    kind: str
    status: str
    message: str
    trade_id: int | None = None
    decision: dict | None = None


class ArmoriqResponse(BaseModel):
    ok: bool = True
    reply: str
    context: dict
    actions: list[ArmoriqActionOut] = Field(default_factory=list)


class NotificationOut(BaseModel):
    id: int
    level: str
    title: str
    message: str
    source: str
    read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyDocumentUpdate(BaseModel):
    email: EmailStr
    updates: dict[str, str | float | int | bool | list[str]] = Field(default_factory=dict)
