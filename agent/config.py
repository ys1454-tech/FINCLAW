from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class AgentRuntimeConfig:
    backend_base_url: str = os.getenv('FINCLAW_BACKEND_URL', 'http://127.0.0.1:8000')
    user_email: str = os.getenv('FINCLAW_AGENT_EMAIL', 'agent@trading.ai')
    tickers: list[str] = field(
        default_factory=lambda: [
            ticker.strip().upper()
            for ticker in os.getenv('FINCLAW_AGENT_TICKERS', 'AAPL,MSFT,NVDA').split(',')
            if ticker.strip()
        ]
    )
    loop_interval_seconds: int = max(10, int(os.getenv('FINCLAW_AGENT_LOOP_INTERVAL', '20')))
    strategy_name: str = os.getenv('FINCLAW_AGENT_STRATEGY', 'conservative-paper-sim')
