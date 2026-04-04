# Intent, Policy, and Enforcement

## Intent Model

Trade intents are structured JSON objects with:
- `user_email`
- `ticker`
- `side`
- `notional_usd`
- `quantity`
- `reason`
- `source`
- `asset_class`
- `mode`

## Policy Model

Runtime policy document:

```json
{
  "max_trade_amount": 100,
  "allowed_tickers": ["AAPL", "MSFT", "NVDA"],
  "blocked_tickers": ["GME"],
  "max_daily_trades": 3,
  "allowed_asset_classes": ["equity", "crypto"],
  "allowed_sources": ["frontend", "automation"],
  "automation_enabled": true,
  "blackout_active": false
}
```

## Enforcement Mechanism

Before execution:
1. sanitize input
2. inspect for adversarial / prompt-injection-like instructions
3. materialize runtime policy from DB-backed document
4. evaluate deterministic policy rules
5. block or allow with explicit rationale
6. record audit logs and application notifications

## Security Controls

Blocked categories include:
- prompt injection attempts
- attempts to bypass policy
- sensitive credential requests
- unauthorized execution sources
- blocked tickers
- disallowed asset classes
- oversized trades
- daily trade cap violations
- blackout / automation disabled conditions
