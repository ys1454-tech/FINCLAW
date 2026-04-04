# FINCLAW

FINCLAW is a submission-ready hackathon prototype for **intent-aware autonomous paper trading**. It separates the UI, API, and agent logic, then forces every trade through a deterministic policy enforcement layer before execution.

## Why this project stands out
- Structured **trade intent** before any execution
- Explicit **policy enforcement** with allow/block decisions
- Real **Alpaca paper trading** integration
- Clear **frontend / backend / agent** separation
- Test coverage for allowed and blocked trade scenarios
- Clean repo layout for evaluator review

## Tech stack
- Frontend: ArmorClaw static HTML, CSS, vanilla JavaScript
- Backend: FastAPI, SQLAlchemy, Pydantic
- Agent: internal automation service
- Trading API: Alpaca Paper Trading
- Database: SQLite
- Testing: pytest, FastAPI TestClient
- Containers: Docker, docker compose

## Repository structure
```text
.
├── agent/
│   ├── client.py
│   ├── config.py
│   ├── main.py
│   └── runner.py
├── backend/
│   ├── app/
│   ├── tests/
│   ├── .env.example
│   ├── Dockerfile
│   ├── requirements.txt
│   └── seed.py
├── docs/
├── frontend/
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Agent integration
FINCLAW includes a dedicated internal `agent/` module for automation control. The agent is designed as a system component, not a chatbot layer.

Typical flow:
1. `agent/` bootstraps runtime configuration
2. it calls backend control endpoints
3. backend automation generates structured trade intents
4. policy enforcement decides allow/block
5. only allowed trades reach Alpaca paper execution
6. ArmorIQ uses `/api/armoriq` to inspect context and optionally trigger safe backend automation
7. logs and decision metadata remain visible for auditability

## Features
- User onboarding and login
- Policy selection and retrieval
- Dashboard and recent trade history
- Structured trade intent API
- Runtime allow/block enforcement
- Agent configure/start/stop/run-once controls
- Audit-friendly decision responses

## Quick start

### Fastest option on Windows
```bat
start_finclaw.bat
```

This launches:
- backend on `http://127.0.0.1:8000`
- frontend on `http://127.0.0.1:3000`
- docs on `http://127.0.0.1:8000/docs`

### Manual backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python seed.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Manual frontend
This repository currently uses the ArmorClaw frontend bundle located here:

```bash
cd "ArmorClawFrontend-main\Armorclaw frontend"
python -m http.server 3000
```

Open:
- Frontend: http://127.0.0.1:3000
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

The frontend is now wired to the live backend for:
- login and onboarding
- policy fetch + save
- dashboard and trades fetch
- paper trade submission
- agent status and controls through the Sentinel panel
- ArmorIQ in-app agent replies through `/api/armoriq`, with optional backend automation execution

The frontend reads the backend base URL from `config.js`, or `window.FINCLAW_API_BASE`, or `localStorage.FINCLAW_API_BASE`. If none are set, it defaults to `http://127.0.0.1:8000`.

## Running tests
```bash
cd backend
pytest
```

## Docker
```bash
docker compose up --build
```

## Environment handling
- Real secrets are **not** committed
- Use `backend/.env.example` as the template
- Submit the real `.env` separately if your evaluation form asks for it

## Deployment
A public deployment is optional. If needed:
- backend -> Render / Railway / Fly.io / AWS App Runner
- frontend -> GitHub Pages / Netlify / Vercel static hosting

## Submission checklist
- Clean project structure
- Professional README
- Env template included
- No `node_modules`, `.env`, `__pycache__`, or tracked build junk intended for submission
- Tests available for backend validation
- Docs included in `docs/`

## Bonus docs
- `docs/DEMO_SCRIPT.md`
- `docs/FIGMA_SUGGESTION.md`
- `docs/ARCHITECTURE.md`
- `docs/INTENT_POLICY_ENFORCEMENT.md`
