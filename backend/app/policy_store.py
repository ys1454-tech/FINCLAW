from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy.orm import Session

from .config import get_settings
from .models import Policy
from .policy_engine import EffectivePolicy, PolicyRule

settings = get_settings()

DEFAULT_POLICY_TEMPLATE = {
    'max_trade_amount': settings.default_max_order_notional,
    'allowed_tickers': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'BTCUSD', 'ETHUSD'],
    'blocked_tickers': ['GME'],
    'max_daily_trades': settings.default_max_daily_trades,
    'allowed_asset_classes': ['equity', 'crypto'],
    'allowed_sources': ['frontend', 'automation'],
    'automation_enabled': True,
    'blackout_active': False,
}


def _policy_map(db: Session, email: str) -> dict[str, Policy]:
    rows = db.query(Policy).filter(Policy.user_email == email).all()
    return {row.title: row for row in rows}


def ensure_policy_seed(db: Session, email: str) -> None:
    existing = _policy_map(db, email)
    for key, value in DEFAULT_POLICY_TEMPLATE.items():
        if key in existing:
            continue
        db.add(Policy(user_email=email, title=key, value=_serialize_value(value), enabled=True))
    db.commit()


def _serialize_value(value: Any) -> str:
    if isinstance(value, list):
        return ','.join(str(v).upper() for v in value)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _parse_value(key: str, value: str) -> Any:
    if key in {'allowed_tickers', 'blocked_tickers', 'allowed_asset_classes', 'allowed_sources'}:
        return [item.strip().upper() if 'ticker' in key else item.strip().lower() for item in value.split(',') if item.strip()]
    if key in {'automation_enabled', 'blackout_active'}:
        return value.strip().lower() == 'true'
    if key in {'max_trade_amount'}:
        return float(value)
    if key in {'max_daily_trades'}:
        return int(float(value))
    return value


def get_runtime_policy(db: Session, email: str) -> dict[str, Any]:
    ensure_policy_seed(db, email)
    items = _policy_map(db, email)
    materialized: dict[str, Any] = {}
    for key, default in DEFAULT_POLICY_TEMPLATE.items():
        row = items.get(key)
        materialized[key] = _parse_value(key, row.value if row else _serialize_value(default))
    return materialized


def build_effective_policy(db: Session, email: str) -> EffectivePolicy:
    runtime = get_runtime_policy(db, email)
    return EffectivePolicy(
        approved_tickers=runtime['allowed_tickers'],
        allowed_asset_classes=runtime['allowed_asset_classes'],
        allowed_sources=runtime['allowed_sources'],
        max_order_notional=runtime['max_trade_amount'],
        max_daily_trades=runtime['max_daily_trades'],
        automation_enabled=runtime['automation_enabled'],
        blocked_tickers=runtime['blocked_tickers'],
        blackout_active=runtime['blackout_active'],
        rules=[
            PolicyRule('approved_universe', 'Ticker must be in approved universe'),
            PolicyRule('blocked_ticker', 'Explicitly blocked tickers cannot execute'),
            PolicyRule('max_order_notional', 'Order notional must remain within policy cap'),
            PolicyRule('max_daily_trades', 'Daily trade count must remain within policy cap'),
            PolicyRule('source_restriction', 'Only approved sources may execute trades'),
            PolicyRule('asset_class_restriction', 'Only approved asset classes may be traded'),
            PolicyRule('automation_disabled', 'Automation may be disabled by runtime policy'),
            PolicyRule('earnings_blackout', 'Blackout windows block all trading'),
        ],
    )


def get_policy_document(db: Session, email: str) -> dict[str, Any]:
    runtime = get_runtime_policy(db, email)
    return {
        'email': email,
        'policy': runtime,
        'rules': [asdict(rule) for rule in build_effective_policy(db, email).rules],
    }


def update_policy_document(db: Session, email: str, updates: dict[str, Any]) -> dict[str, Any]:
    ensure_policy_seed(db, email)
    existing = _policy_map(db, email)
    for key, value in updates.items():
        serialized = _serialize_value(value)
        if key in existing:
            existing[key].value = serialized
            existing[key].enabled = True
        else:
            db.add(Policy(user_email=email, title=key, value=serialized, enabled=True))
    db.commit()
    return get_policy_document(db, email)
