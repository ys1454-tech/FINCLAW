from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PolicyRule:
    rule_id: str
    description: str
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class EffectivePolicy:
    approved_tickers: list[str]
    allowed_asset_classes: list[str]
    allowed_sources: list[str]
    max_order_notional: float
    max_daily_trades: int
    automation_enabled: bool = True
    blocked_tickers: list[str] = field(default_factory=list)
    blackout_active: bool = False
    rules: list[PolicyRule] = field(default_factory=list)


@dataclass
class IntentDecision:
    allowed: bool
    decision: str
    rule_id: str
    rationale: str
    evaluated_at: str


def evaluate_trade_intent(intent: dict[str, Any], policy: EffectivePolicy, today_trade_count: int) -> IntentDecision:
    ticker = str(intent.get('ticker', '')).upper()
    source = str(intent.get('source', '')).lower()
    asset_class = str(intent.get('asset_class', 'equity')).lower()
    notional = float(intent.get('notional_usd', 0))

    now = datetime.now(timezone.utc).isoformat()

    if not policy.automation_enabled and source == 'automation':
        return IntentDecision(False, 'block', 'automation_disabled', 'Automation is disabled by policy.', now)

    if policy.blackout_active:
        return IntentDecision(False, 'block', 'earnings_blackout', 'Trading is blocked during blackout window.', now)

    if ticker in {item.upper() for item in policy.blocked_tickers}:
        return IntentDecision(False, 'block', 'blocked_ticker', f'{ticker} is explicitly blocked by policy.', now)

    if ticker not in {item.upper() for item in policy.approved_tickers}:
        return IntentDecision(False, 'block', 'approved_universe', f'{ticker} is not in the approved ticker universe.', now)

    if asset_class not in {item.lower() for item in policy.allowed_asset_classes}:
        return IntentDecision(False, 'block', 'asset_class_restriction', f'Asset class {asset_class} is not allowed.', now)

    if source not in {item.lower() for item in policy.allowed_sources}:
        return IntentDecision(False, 'block', 'source_restriction', f'Source {source} is not allowed to execute trades.', now)

    if notional > policy.max_order_notional:
        return IntentDecision(False, 'block', 'max_order_notional', f'Order notional ${notional:.2f} exceeds max allowed ${policy.max_order_notional:.2f}.', now)

    if today_trade_count >= policy.max_daily_trades:
        return IntentDecision(False, 'block', 'max_daily_trades', f'Daily trade limit of {policy.max_daily_trades} reached.', now)

    return IntentDecision(True, 'allow', 'within_policy', 'Intent satisfies all active policy rules.', now)
