from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .alpaca_client import AlpacaPaperTrader
from .automation import automation_agent
from .config import get_settings
from .database import Base, engine, get_db
from .logging_config import configure_logging
from .schemas import ArmoriqRequest, AgentConfigRequest, ChatRequest, LoginRequest, OnboardingRequest, PolicyDocumentUpdate, PolicySelectionRequest, TradeIntent
from .policy_store import get_policy_document, update_policy_document
from .security_controls import inspect_user_input
from .services import (
    add_audit_log,
    armoriq_reply,
    authenticate_user,
    bootstrap_user,
    chat_reply,
    create_notification,
    create_trade,
    get_enabled_policies,
    get_notifications,
    get_portfolio_summary,
    get_recent_trades,
    replace_policies,
    validate_trade,
)

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)
trader = AlpacaPaperTrader()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info('FinClaw API starting in %s mode', settings.app_env)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'] if settings.cors_origins == '*' else [o.strip() for o in settings.cors_origins.split(',') if o.strip()],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception('Unhandled error for %s %s', request.method, request.url.path)
    return JSONResponse(status_code=500, content={'ok': False, 'detail': 'Internal server error'})


@app.get('/health')
def health():
    return {'ok': True, 'app': settings.app_name, 'env': settings.app_env}


@app.post('/api/auth/login')
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid email or password')
    return {'ok': True, 'user': {'email': user.email, 'goal': user.goal, 'risk': user.risk, 'asset': user.asset}}


@app.post('/api/auth/onboarding')
def onboarding(payload: OnboardingRequest, db: Session = Depends(get_db)):
    user = bootstrap_user(db, payload.email, payload.password, payload.goal, payload.experience, payload.risk, payload.asset)
    return {'ok': True, 'user': {'email': user.email, 'goal': user.goal, 'risk': user.risk, 'asset': user.asset}}


@app.post('/api/policies')
def save_policies(payload: PolicySelectionRequest, db: Session = Depends(get_db)):
    replace_policies(db, payload.email, [p.model_dump() for p in payload.policies])
    return {'ok': True}


@app.get('/api/policies/{email}')
def fetch_policies(email: str, db: Session = Depends(get_db)):
    items = get_enabled_policies(db, email)
    return {'ok': True, 'policies': [{'title': i.title, 'value': i.value, 'enabled': i.enabled} for i in items]}


@app.get('/api/dashboard/{email}')
def dashboard(email: str, db: Session = Depends(get_db)):
    return {'ok': True, 'data': get_portfolio_summary(db, email)}


@app.get('/api/trades/{email}')
def trades(email: str, db: Session = Depends(get_db)):
    rows = get_recent_trades(db, email=email, limit=20)
    return {
        'ok': True,
        'trades': [
            {
                'id': t.id,
                'asset': t.asset,
                'type': t.trade_type,
                'amount': t.amount,
                'pnl_percent': t.pnl_percent,
                'status': t.status,
                'auto_ai': t.auto_ai,
                'execution_reason': t.execution_reason,
                'created_at': t.created_at.isoformat(),
            }
            for t in rows
        ],
    }


@app.post('/api/chat')
def chat(payload: ChatRequest):
    return {'ok': True, 'reply': chat_reply(payload.message)}


@app.get('/api/policy/{email}')
def get_policy(email: str, db: Session = Depends(get_db)):
    return {'ok': True, **get_policy_document(db, email)}


@app.post('/api/policy')
def update_policy(payload: PolicyDocumentUpdate, db: Session = Depends(get_db)):
    document = update_policy_document(db, payload.email, payload.updates)
    add_audit_log(db, payload.email, 'policy_update', 'allowed', 'Runtime policy document updated.', str(payload.updates))
    create_notification(db, payload.email, 'Policy updated', 'Runtime policy document changed successfully.', level='info', source='policy-engine')
    return {'ok': True, **document}


@app.post('/api/armoriq')
def armoriq(payload: ArmoriqRequest, db: Session = Depends(get_db)):
    inspection = inspect_user_input(payload.message)
    if not inspection.allowed and payload.email:
        add_audit_log(db, payload.email, 'armoriq_input', 'blocked', inspection.reason, payload.message)
        create_notification(db, payload.email, 'Security block', inspection.reason, level='warning', source='armoriq')
        return {'ok': True, 'reply': inspection.reason, 'context': {'security_tags': inspection.tags}, 'actions': []}

    result = armoriq_reply(db, inspection.sanitized_message, payload.email)

    if payload.auto_execute and payload.email:
        executed_actions: list[dict] = []
        for action in result.get('actions', []):
            if action.get('kind') != 'agent':
                continue
            command = action.get('command')
            if command == 'run-once':
                agent = automation_agent.run_once()
                action['status'] = 'executed'
                action['message'] = 'Backend automation cycle executed through FINCLAW.'
                result['context']['agent'] = agent
                executed_actions.append(action)
            elif command == 'start':
                agent = automation_agent.start()
                action['status'] = 'executed'
                action['message'] = 'Backend automation started through FINCLAW.'
                result['context']['agent'] = agent
                executed_actions.append(action)
            elif command == 'stop':
                agent = automation_agent.stop()
                action['status'] = 'executed'
                action['message'] = 'Backend automation stopped through FINCLAW.'
                result['context']['agent'] = agent
                executed_actions.append(action)

        if executed_actions:
            result['reply'] += ' The requested FINCLAW automation command was executed through the live backend.'

    return {'ok': True, **result}


@app.post('/api/trade-intents')
def trade_intent(payload: TradeIntent, db: Session = Depends(get_db)):
    intent = payload.model_dump()
    allowed, reason, decision = validate_trade(db, intent)
    if not allowed:
        add_audit_log(db, payload.user_email, 'trade_intent', 'blocked', reason, payload.model_dump_json())
        create_notification(db, payload.user_email, 'Trade blocked', reason, level='warning', source='policy-engine')
        raise HTTPException(status_code=403, detail={'reason': reason, 'decision': decision})

    broker_result = trader.submit_market_order(payload.ticker.upper(), payload.side, payload.notional_usd)
    trade = create_trade(
        db,
        email=payload.user_email,
        asset=payload.ticker,
        trade_type=payload.side,
        amount=payload.notional_usd,
        quantity=payload.quantity or 0,
        reason=f"{reason} Execution mode: {broker_result['mode']}.",
        auto_ai=True,
        status=str(broker_result.get('status', 'accepted')),
    )
    add_audit_log(db, payload.user_email, 'trade_intent', 'allowed', reason, payload.model_dump_json())
    create_notification(db, payload.user_email, 'Trade accepted', f"{payload.side.upper()} {payload.ticker.upper()} for ${payload.notional_usd:,.2f} was accepted via {broker_result['mode']}.", level='success', source='execution-engine')
    return {'ok': True, 'trade_id': trade.id, 'broker_result': broker_result, 'reason': reason, 'decision': decision}


@app.get('/api/agent/status')
def agent_status():
    return {'ok': True, 'agent': automation_agent.get_status()}


@app.post('/api/agent/configure')
def agent_configure(payload: AgentConfigRequest):
    status = automation_agent.configure(
        user_email=payload.user_email,
        tickers=payload.tickers or None,
        loop_interval_seconds=payload.loop_interval_seconds,
    )
    return {'ok': True, 'agent': status}


@app.post('/api/agent/start')
def agent_start():
    return {'ok': True, 'agent': automation_agent.start()}


@app.post('/api/agent/stop')
def agent_stop():
    return {'ok': True, 'agent': automation_agent.stop()}


@app.post('/api/agent/run-once')
def agent_run_once():
    return {'ok': True, 'agent': automation_agent.run_once()}


@app.get('/api/notifications/{email}')
def notifications(email: str, db: Session = Depends(get_db)):
    items = get_notifications(db, email, limit=20)
    return {
        'ok': True,
        'notifications': [
            {
                'id': item.id,
                'level': item.level,
                'title': item.title,
                'message': item.message,
                'source': item.source,
                'read': item.read,
                'created_at': item.created_at.isoformat(),
            }
            for item in items
        ],
    }
