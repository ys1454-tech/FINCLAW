# FINCLAW Backend

FastAPI backend for FINCLAW.

## Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Seed demo data
```powershell
.\.venv\Scripts\python seed.py
```

## Run server
```powershell
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Test
```powershell
.\.venv\Scripts\python -m pytest
```

## Endpoints
- `/health`
- `/docs`
- `/api/auth/login`
- `/api/auth/onboarding`
- `/api/policies`
- `/api/dashboard/{email}`
- `/api/trades/{email}`
- `/api/trade-intents`
- `/api/agent/status`
- `/api/agent/configure`
- `/api/agent/start`
- `/api/agent/stop`
- `/api/agent/run-once`
