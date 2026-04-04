from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .alpaca_client import AlpacaPaperTrader
from .database import SessionLocal
from .services import add_audit_log, create_notification, create_trade, validate_trade


@dataclass
class AgentState:
    enabled: bool = False
    running: bool = False
    loop_interval_seconds: int = 20
    user_email: str = 'agent@trading.ai'
    strategy_name: str = 'conservative-paper-sim'
    tickers: list[str] = field(default_factory=lambda: ['AAPL', 'MSFT', 'NVDA'])
    last_tick_at: str | None = None
    last_action: str = 'idle'
    last_error: str | None = None
    last_decision: dict[str, Any] | None = None
    simulated_price_index: int = 0
    logs: list[dict[str, Any]] = field(default_factory=list)


class TradingAutomationAgent:
    def __init__(self) -> None:
        self.state = AgentState()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._trader = AlpacaPaperTrader()

    def _append_log(self, level: str, message: str, **extra: Any) -> None:
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level,
            'message': message,
            **extra,
        }
        with self._lock:
            self.state.logs.append(entry)
            self.state.logs = self.state.logs[-100:]
            self.state.last_action = message
            self.state.last_tick_at = entry['timestamp']
            if level == 'error':
                self.state.last_error = message
            if 'decision' in extra:
                self.state.last_decision = extra['decision']

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                'enabled': self.state.enabled,
                'running': self.state.running,
                'loop_interval_seconds': self.state.loop_interval_seconds,
                'user_email': self.state.user_email,
                'strategy_name': self.state.strategy_name,
                'tickers': list(self.state.tickers),
                'last_tick_at': self.state.last_tick_at,
                'last_action': self.state.last_action,
                'last_error': self.state.last_error,
                'last_decision': self.state.last_decision,
                'logs': list(self.state.logs[-20:]),
            }

    def configure(self, *, user_email: str | None = None, tickers: list[str] | None = None, loop_interval_seconds: int | None = None) -> dict[str, Any]:
        with self._lock:
            if user_email:
                self.state.user_email = user_email
            if tickers:
                self.state.tickers = [ticker.upper() for ticker in tickers]
            if loop_interval_seconds:
                self.state.loop_interval_seconds = max(10, min(loop_interval_seconds, 3600))
        self._append_log('info', 'agent configuration updated', user_email=self.state.user_email, tickers=self.state.tickers)
        return self.get_status()

    def start(self) -> dict[str, Any]:
        with self._lock:
            self.state.enabled = True
            if self.state.running:
                return self.get_status()
            self.state.running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
        self._append_log('info', 'automation agent started')
        return self.get_status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self.state.enabled = False
            self.state.running = False
        self._append_log('info', 'automation agent stopped')
        return self.get_status()

    def run_once(self) -> dict[str, Any]:
        self._execute_cycle()
        return self.get_status()

    def _run_loop(self) -> None:
        while True:
            with self._lock:
                if not self.state.enabled:
                    self.state.running = False
                    break
                interval = self.state.loop_interval_seconds
            self._execute_cycle()
            time.sleep(interval)

    def _execute_cycle(self) -> None:
        db = SessionLocal()
        try:
            ticker = self.state.tickers[self.state.simulated_price_index % len(self.state.tickers)]
            side = 'buy' if self.state.simulated_price_index % 2 == 0 else 'sell'
            notional = random.choice([20.0, 25.0, 30.0])
            self.state.simulated_price_index += 1

            intent = {
                'user_email': self.state.user_email,
                'ticker': ticker,
                'side': side,
                'notional_usd': notional,
                'quantity': 1,
                'reason': f'Automation strategy {self.state.strategy_name}',
                'source': 'automation',
                'asset_class': 'equity',
                'mode': 'paper',
            }

            allowed, reason, decision = validate_trade(db, intent)
            if not allowed:
                add_audit_log(db, self.state.user_email, 'automation_cycle', 'blocked', reason, str(intent))
                create_notification(db, self.state.user_email, 'Automation blocked', reason, level='warning', source='automation-agent')
                self._append_log('warning', f'cycle blocked: {reason}', ticker=ticker, side=side, notional=notional, decision=decision)
                return

            broker_result = self._trader.submit_market_order(ticker, side, notional)
            trade = create_trade(
                db,
                email=self.state.user_email,
                asset=ticker,
                trade_type=side,
                amount=notional,
                quantity=1,
                reason=f'{reason} Execution mode: {broker_result.get("mode", "simulated")}.',
                auto_ai=True,
                status=str(broker_result.get('status', 'accepted')),
            )
            add_audit_log(db, self.state.user_email, 'automation_cycle', 'allowed', reason, str(intent))
            create_notification(db, self.state.user_email, 'Automation executed', f'{side.upper()} {ticker} for ${notional:,.2f} executed via {broker_result.get("mode", "simulated")}.', level='success', source='automation-agent')
            self._append_log('info', f'executed {side} {ticker}', ticker=ticker, side=side, notional=notional, trade_id=trade.id, broker_mode=broker_result.get('mode', 'simulated'), decision=decision)
        except Exception as exc:
            create_notification(db, self.state.user_email, 'Automation error', str(exc), level='error', source='automation-agent')
            self._append_log('error', f'automation cycle failed: {exc}')
        finally:
            db.close()


automation_agent = TradingAutomationAgent()
