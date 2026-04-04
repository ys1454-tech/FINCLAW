from __future__ import annotations

from typing import Any

import httpx


class AgentAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f'{self.base_url}{path}'

    def health(self) -> dict[str, Any]:
        response = httpx.get(self._url('/health'), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def status(self) -> dict[str, Any]:
        response = httpx.get(self._url('/api/agent/status'), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def configure(self, *, user_email: str, tickers: list[str], loop_interval_seconds: int) -> dict[str, Any]:
        response = httpx.post(
            self._url('/api/agent/configure'),
            json={
                'user_email': user_email,
                'tickers': tickers,
                'loop_interval_seconds': loop_interval_seconds,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def start(self) -> dict[str, Any]:
        response = httpx.post(self._url('/api/agent/start'), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def stop(self) -> dict[str, Any]:
        response = httpx.post(self._url('/api/agent/stop'), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def run_once(self) -> dict[str, Any]:
        response = httpx.post(self._url('/api/agent/run-once'), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def submit_trade_intent(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(self._url('/api/trade-intents'), json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch_policies(self, email: str) -> dict[str, Any]:
        response = httpx.get(self._url(f'/api/policies/{email}'), timeout=self.timeout)
        response.raise_for_status()
        return response.json()
