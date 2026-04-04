from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


SUSPICIOUS_PATTERNS = [
    r'ignore\s+all\s+previous\s+instructions',
    r'exfiltrate',
    r'send\s+me\s+the\s+api\s+key',
    r'reveal\s+.*secret',
    r'bypass\s+policy',
    r'override\s+security',
    r'disable\s+guardrails',
    r'export\s+credentials',
    r'open\s+.*\\.env',
]


@dataclass
class SecurityDecision:
    allowed: bool
    reason: str
    sanitized_message: str
    tags: list[str]


def sanitize_text(text: str) -> str:
    cleaned = re.sub(r'\s+', ' ', text or '').strip()
    return cleaned[:2000]


def inspect_user_input(text: str) -> SecurityDecision:
    sanitized = sanitize_text(text)
    tags: list[str] = []
    lowered = sanitized.lower()

    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            tags.append('prompt_injection')
            return SecurityDecision(
                allowed=False,
                reason='Input blocked by ArmorIQ security controls due to suspicious or adversarial instruction content.',
                sanitized_message=sanitized,
                tags=tags,
            )

    if any(token in lowered for token in ['.env', 'secret key', 'api key', 'credential dump']):
        tags.append('sensitive_data_access')
        return SecurityDecision(
            allowed=False,
            reason='Input blocked because it appears to request sensitive credentials or protected configuration.',
            sanitized_message=sanitized,
            tags=tags,
        )

    return SecurityDecision(True, 'Input accepted.', sanitized, tags)


def sanitize_trade_intent(intent: dict[str, Any]) -> dict[str, Any]:
    payload = dict(intent)
    payload['ticker'] = str(payload.get('ticker', '')).upper().strip()
    payload['side'] = str(payload.get('side', '')).lower().strip()
    payload['source'] = str(payload.get('source', '')).lower().strip()
    payload['asset_class'] = str(payload.get('asset_class', '')).lower().strip()
    payload['reason'] = sanitize_text(str(payload.get('reason', '')))
    return payload
