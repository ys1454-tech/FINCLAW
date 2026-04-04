from __future__ import annotations

from typing import Any
from .config import get_settings

settings = get_settings()

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
except Exception:
    TradingClient = None
    MarketOrderRequest = None
    OrderSide = None
    TimeInForce = None


class AlpacaPaperTrader:
    def __init__(self) -> None:
        self.enabled = bool(settings.alpaca_api_key and settings.alpaca_secret_key and TradingClient)
        self.client = None
        if self.enabled:
            self.client = TradingClient(settings.alpaca_api_key, settings.alpaca_secret_key, paper=settings.alpaca_paper)

    def submit_market_order(self, symbol: str, side: str, notional_usd: float) -> dict[str, Any]:
        if not self.enabled:
            return {
                'mode': 'simulated',
                'status': 'accepted',
                'symbol': symbol,
                'side': side,
                'notional': notional_usd,
                'message': 'Alpaca keys not configured; simulated paper execution only.'
            }

        order = MarketOrderRequest(
            symbol=symbol,
            notional=notional_usd,
            side=OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        submitted = self.client.submit_order(order_data=order)
        return {
            'mode': 'alpaca',
            'status': getattr(submitted, 'status', 'accepted'),
            'id': str(getattr(submitted, 'id', '')),
            'symbol': symbol,
            'side': side,
            'notional': notional_usd,
        }
