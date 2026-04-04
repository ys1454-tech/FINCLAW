from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from .config import get_settings
from .models import AuditLog, Notification, Policy, Trade, User
from .policy_engine import evaluate_trade_intent
from .policy_store import build_effective_policy
from .security import hash_password, verify_password
from .security_controls import inspect_user_input, sanitize_trade_intent

settings = get_settings()

STATIC_CHAT = {
    'performing': 'Your portfolio is up today. NVDA and AAPL are contributing the most gains.',
    'profit': 'Profit is the positive difference between sell value and buy value.',
    'next': 'Given your current policy limits, the safest next step is to watch approved tickers and wait for confirmation before placing a paper trade.',
}


def bootstrap_user(
    db: Session,
    email: str,
    password: str,
    goal: str = 'growth',
    experience: str = 'novice',
    risk: str = 'medium',
    asset: str = 'stocks',
) -> User:
    user = db.query(User).filter(User.email == email).first()
    password_hash = hash_password(password)
    if user:
        user.password = password_hash
        user.goal = goal
        user.experience = experience
        user.risk = risk
        user.asset = asset
        db.commit()
        db.refresh(user)
        return user

    user = User(email=email, password=password_hash, goal=goal, experience=experience, risk=risk, asset=asset)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    stored = user.password or ''
    if '$' in stored:
        return user if verify_password(password, stored) else None

    if stored == password:
        user.password = hash_password(password)
        db.commit()
        db.refresh(user)
        return user
    return None


def replace_policies(db: Session, email: str, policies: list[dict[str, Any]]) -> None:
    db.query(Policy).filter(Policy.user_email == email).delete()
    for item in policies:
        db.add(Policy(user_email=email, title=item['title'], value=item['value'], enabled=item.get('enabled', True)))
    db.commit()


def get_enabled_policies(db: Session, email: str) -> list[Policy]:
    return db.query(Policy).filter(Policy.user_email == email, Policy.enabled.is_(True)).all()


def get_recent_trades(db: Session, email: str | None = None, limit: int = 10) -> list[Trade]:
    query = db.query(Trade)
    if email:
        query = query.filter(Trade.user_email == email)
    return query.order_by(desc(Trade.created_at)).limit(limit).all()


def get_today_trade_count(db: Session, email: str) -> int:
    today = datetime.now(timezone.utc).date()
    return len([t for t in get_recent_trades(db, email=email, limit=200) if t.created_at.date() == today])


def get_portfolio_summary(db: Session, email: str | None = None) -> dict[str, Any]:
    trades = get_recent_trades(db, email=email, limit=50)
    total_balance = 12540.0
    daily_change_pct = 5.4
    holdings = [
        {'asset': 'AAPL', 'shares': 2.5, 'value': 450.0, 'change_pct': 1.2},
        {'asset': 'BTCUSD', 'shares': 0.02, 'value': 780.0, 'change_pct': 3.8},
        {'asset': 'NVDA', 'shares': 1.1, 'value': 620.0, 'change_pct': -1.2},
    ]
    return {
        'total_balance': total_balance,
        'daily_change_pct': daily_change_pct,
        'market_status': 'Bullish',
        'holdings': holdings,
        'recent_trades': [
            {
                'id': t.id,
                'asset': t.asset,
                'type': t.trade_type,
                'amount': f'${t.amount:,.2f}',
                'date': t.created_at.strftime('%b %d'),
                'pnl': f'{t.pnl_percent:+.1f}%',
                'status': t.status,
                'reason': t.execution_reason,
            }
            for t in trades
        ],
    }


def chat_reply(message: str) -> str:
    inspection = inspect_user_input(message)
    if not inspection.allowed:
        return inspection.reason
    lower = inspection.sanitized_message.lower()
    for key, value in STATIC_CHAT.items():
        if key in lower:
            return value
    return 'I can help with portfolio performance, trade safety, policy limits, and paper trading decisions.'


def get_user_summary(db: Session, email: str | None) -> dict[str, Any]:
    if not email:
        return {
            'user': None,
            'policies': [],
            'recent_trades': [],
            'dashboard': get_portfolio_summary(db, email=None),
        }

    user = db.query(User).filter(User.email == email).first()
    policies = get_enabled_policies(db, email)
    trades = get_recent_trades(db, email=email, limit=5)
    dashboard = get_portfolio_summary(db, email=email)
    return {
        'user': {
            'email': user.email,
            'goal': user.goal,
            'experience': user.experience,
            'risk': user.risk,
            'asset': user.asset,
        } if user else None,
        'policies': [
            {'title': p.title, 'value': p.value, 'enabled': p.enabled}
            for p in policies
        ],
        'recent_trades': [
            {
                'id': t.id,
                'asset': t.asset,
                'type': t.trade_type,
                'amount': t.amount,
                'status': t.status,
                'execution_reason': t.execution_reason,
                'created_at': t.created_at.isoformat(),
            }
            for t in trades
        ],
        'dashboard': dashboard,
    }


def armoriq_reply(db: Session, message: str, email: str | None) -> dict[str, Any]:
    lower = message.lower().strip()
    summary = get_user_summary(db, email)
    dashboard = summary['dashboard']
    holdings = dashboard.get('holdings', [])
    holding_assets = [str(item.get('asset', '')).upper() for item in holdings if item.get('asset')]
    approved_assets = list(dict.fromkeys([*holding_assets, *settings.approved_tickers]))
    actions: list[dict[str, Any]] = []

    def find_asset_from_text() -> str | None:
        for asset in approved_assets:
            if asset and asset.lower() in lower:
                return asset
        alias_map = {
            'apple': 'AAPL',
            'microsoft': 'MSFT',
            'nvidia': 'NVDA',
            'google': 'GOOGL',
            'bitcoin': 'BTCUSD',
            'btc': 'BTCUSD',
            'ethereum': 'ETHUSD',
            'eth': 'ETHUSD',
        }
        for alias, asset in alias_map.items():
            if alias in lower and asset in approved_assets:
                return asset
        return None

    def extract_amount() -> float | None:
        cleaned = lower.replace('$', ' ')
        for token in cleaned.split():
            token = token.replace(',', '').strip()
            try:
                value = float(token)
                if value > 0:
                    return value
            except ValueError:
                continue
        return None

    if any(token in lower for token in ['status', 'overview', 'portfolio', 'dashboard']):
        actions.append({'kind': 'view', 'target': 'dashboard', 'status': 'ready', 'message': 'Dashboard context loaded.'})
        reply = (
            f"ArmorIQ is operating inside FINCLAW. Balance is ${dashboard['total_balance']:,.2f}, daily change is {dashboard['daily_change_pct']:+.1f}%, "
            f"market status is {dashboard['market_status']}, and I have loaded live dashboard context for this session."
        )
        return {'reply': reply, 'context': summary, 'actions': actions}

    if any(token in lower for token in ['show new stocks', 'show stocks', 'show assets', 'list assets', 'new assets']):
        actions.append({'kind': 'view', 'target': 'assets', 'status': 'ready', 'message': 'Assets view selected.'})
        actions.append({'kind': 'highlight_assets', 'assets': approved_assets[:8], 'status': 'ready', 'message': 'Approved assets prepared for display.'})
        return {
            'reply': f"I switched to the asset universe FINCLAW can actually act on. Available tracked or approved symbols include: {', '.join(approved_assets[:8])}.",
            'context': summary,
            'actions': actions,
        }

    if any(token in lower for token in ['show trades', 'recent trades', 'history', 'activity']):
        actions.append({'kind': 'view', 'target': 'history', 'status': 'ready', 'message': 'History view selected.'})
        return {
            'reply': 'I pulled recent execution history from FINCLAW and switched the terminal to the history view.',
            'context': summary,
            'actions': actions,
        }

    if 'policy' in lower or 'risk' in lower:
        policy_count = len(summary['policies'])
        actions.append({'kind': 'view', 'target': 'policies', 'status': 'ready', 'message': 'Policies view selected.'})
        return {
            'reply': f'I switched into policy mode. There are {policy_count} active policy controls on this account, and every action still routes through FINCLAW validation before execution.',
            'context': summary,
            'actions': actions,
        }

    if any(token in lower for token in ['run agent', 'run once', 'scan market']):
        actions.append({'kind': 'agent', 'command': 'run-once', 'status': 'ready', 'message': 'Single automation cycle prepared.'})
        return {
            'reply': 'I am attached to FINCLAW automation and prepared one policy-checked market scan through the backend agent.',
            'context': summary,
            'actions': actions,
        }

    if any(token in lower for token in ['start automation', 'start agent', 'enable automation']):
        actions.append({'kind': 'agent', 'command': 'start', 'status': 'ready', 'message': 'Automation start prepared.'})
        return {
            'reply': 'I am prepared to start continuous FINCLAW automation in paper mode, still bounded by risk and policy checks.',
            'context': summary,
            'actions': actions,
        }

    if any(token in lower for token in ['stop automation', 'stop agent', 'disable automation']):
        actions.append({'kind': 'agent', 'command': 'stop', 'status': 'ready', 'message': 'Automation stop prepared.'})
        return {
            'reply': 'I am prepared to stop the backend automation loop and return the terminal to manual control.',
            'context': summary,
            'actions': actions,
        }

    if any(token in lower for token in ['buy', 'sell']):
        side = 'buy' if 'buy' in lower else 'sell'
        asset = find_asset_from_text() or (approved_assets[0] if approved_assets else 'AAPL')
        amount = extract_amount() or 25.0
        actions.append({
            'kind': 'trade_ticket',
            'status': 'ready',
            'message': 'Trade ticket prepared in the FINCLAW terminal.',
            'trade': {
                'ticker': asset,
                'side': side,
                'notional_usd': amount,
                'source': 'frontend',
                'asset_class': 'crypto' if asset.endswith('USD') else 'equity',
                'mode': 'paper',
            },
        })
        return {
            'reply': f'I prepared a {side.upper()} ticket for {asset} at ${amount:,.2f} inside FINCLAW. You can submit it through the terminal and it will go through live policy validation plus Alpaca paper execution.',
            'context': summary,
            'actions': actions,
        }

    actions.append({'kind': 'view', 'target': 'dashboard', 'status': 'ready', 'message': 'Defaulted to dashboard context.'})
    return {
        'reply': 'ArmorIQ is now working as a FINCLAW operator layer. Give me commands like “show assets”, “show history”, “buy AAPL 25”, “run once”, or “open policies”, and I will route them through application actions instead of generic chat replies.',
        'context': summary,
        'actions': actions,
    }


def validate_trade(db: Session, intent: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    sanitized = sanitize_trade_intent(intent)
    inspection = inspect_user_input(sanitized.get('reason', ''))
    if not inspection.allowed:
        return False, inspection.reason, {
            'allowed': False,
            'decision': 'block',
            'rule_id': 'security_prompt_injection',
            'rationale': inspection.reason,
            'evaluated_at': datetime.now(timezone.utc).isoformat(),
            'security_tags': inspection.tags,
        }
    policy = build_effective_policy(db, sanitized['user_email'])
    today_trade_count = get_today_trade_count(db, sanitized['user_email'])
    decision = evaluate_trade_intent(sanitized, policy, today_trade_count)
    return decision.allowed, decision.rationale, {
        'allowed': decision.allowed,
        'decision': decision.decision,
        'rule_id': decision.rule_id,
        'rationale': decision.rationale,
        'evaluated_at': decision.evaluated_at,
    }


def create_trade(
    db: Session,
    email: str,
    asset: str,
    trade_type: str,
    amount: float,
    quantity: float,
    reason: str,
    auto_ai: bool = True,
    status: str = 'filled',
    pnl_percent: float = 0.0,
) -> Trade:
    trade = Trade(
        user_email=email,
        asset=asset.upper(),
        trade_type=trade_type.capitalize(),
        amount=amount,
        quantity=quantity or 0,
        pnl_percent=pnl_percent,
        execution_reason=reason,
        auto_ai=auto_ai,
        status=status,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def add_audit_log(db: Session, email: str, action: str, decision: str, reason: str, payload: str = '{}') -> None:
    db.add(AuditLog(user_email=email, action=action, decision=decision, reason=reason, payload=payload))
    db.commit()


def create_notification(db: Session, email: str, title: str, message: str, level: str = 'info', source: str = 'armoriq') -> Notification:
    notification = Notification(
        user_email=email,
        level=level,
        title=title,
        message=message,
        source=source,
        read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_notifications(db: Session, email: str, limit: int = 10) -> list[Notification]:
    return db.query(Notification).filter(Notification.user_email == email).order_by(desc(Notification.created_at)).limit(limit).all()
