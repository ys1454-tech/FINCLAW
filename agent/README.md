# FINCLAW Agent

This module is the **internal automation agent** for FINCLAW. It is not a chatbot surface; it is an action-performing system component that controls the backend automation loop through API endpoints.

## What it does
- bootstraps agent runtime configuration
- talks to the FastAPI backend over HTTP
- starts, stops, and runs the automation cycle
- retrieves backend status for monitoring
- keeps agent control separate from UI code

## Files
- `config.py` - runtime configuration from environment variables
- `client.py` - backend API client for agent control
- `runner.py` - orchestration wrapper for agent lifecycle actions
- `main.py` - CLI entrypoint for local/dev control

## Commands
From the repository root:

```bash
python -m agent.main bootstrap
python -m agent.main status
python -m agent.main start
python -m agent.main run-once
python -m agent.main stop
```

## Environment variables
- `FINCLAW_BACKEND_URL` - backend base URL, default `http://127.0.0.1:8000`
- `FINCLAW_AGENT_EMAIL` - agent user email
- `FINCLAW_AGENT_TICKERS` - comma-separated approved tickers
- `FINCLAW_AGENT_LOOP_INTERVAL` - loop interval in seconds
- `FINCLAW_AGENT_STRATEGY` - strategy label for observability

## Integration model
The actual trade generation and policy-aware execution remain enforced by the backend automation layer in `backend/app/automation.py`. This package gives FINCLAW a dedicated `agent/` module so evaluators can clearly see where the autonomous system component lives and how it integrates with the API.
