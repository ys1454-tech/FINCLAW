from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .client import AgentAPIClient
from .config import AgentRuntimeConfig


class AgentRunner:
    """Thin runtime wrapper that treats FINCLAW's agent as a system component, not a chat surface."""

    def __init__(self, config: AgentRuntimeConfig | None = None, client: AgentAPIClient | None = None) -> None:
        self.config = config or AgentRuntimeConfig()
        self.client = client or AgentAPIClient(self.config.backend_base_url)

    def bootstrap(self) -> dict[str, Any]:
        self.client.health()
        return self.client.configure(
            user_email=self.config.user_email,
            tickers=self.config.tickers,
            loop_interval_seconds=self.config.loop_interval_seconds,
        )

    def start(self) -> dict[str, Any]:
        return self.client.start()

    def stop(self) -> dict[str, Any]:
        return self.client.stop()

    def run_once(self) -> dict[str, Any]:
        return self.client.run_once()

    def status(self) -> dict[str, Any]:
        return self.client.status()

    def describe(self) -> dict[str, Any]:
        return {
            'runtime': asdict(self.config),
            'status': self.status(),
        }
