# FINCLAW Architecture

## Runtime Layers

1. **Agent Layer**
   - `agent/` runtime wrapper and backend automation loop
   - Generates structured trade intents only
   - Cannot bypass backend execution controls

2. **Policy / Enforcement Layer**
   - `backend/app/policy_store.py`
   - `backend/app/policy_engine.py`
   - `backend/app/security_controls.py`
   - Applies deterministic runtime checks before every execution

3. **Execution Layer**
   - `backend/app/alpaca_client.py`
   - Executes allowed orders against Alpaca paper trading only

## Lifecycle

Intent → Security inspection → Policy validation → Allow/Block decision → Execution (if allowed) → Audit log + Notification

## Why judges care

- reasoning is separated from execution
- enforcement is visible and deterministic
- blocked actions never reach paper execution
- notifications and logs preserve rationale for every decision
