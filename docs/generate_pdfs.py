from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER

W, H = A4
ORANGE = colors.HexColor('#F97316')
DARK = colors.HexColor('#0F172A')
GRAY = colors.HexColor('#64748B')
LIGHT = colors.HexColor('#F8FAFC')
WHITE = colors.white

def base_styles():
    s = getSampleStyleSheet()
    def add(name, **kw):
        if name not in s:
            s.add(ParagraphStyle(name, **kw))
    add('TitlePage', fontName='Helvetica-Bold', fontSize=28, textColor=WHITE, alignment=TA_CENTER, spaceAfter=8)
    add('SubTitle', fontName='Helvetica', fontSize=13, textColor=ORANGE, alignment=TA_CENTER, spaceAfter=6)
    add('H1', fontName='Helvetica-Bold', fontSize=16, textColor=ORANGE, spaceBefore=14, spaceAfter=6)
    add('H2', fontName='Helvetica-Bold', fontSize=13, textColor=DARK, spaceBefore=10, spaceAfter=4)
    add('Body', fontName='Helvetica', fontSize=10, textColor=DARK, spaceAfter=4, leading=15)
    add('Bullet', fontName='Helvetica', fontSize=10, textColor=DARK, spaceAfter=3, leftIndent=16, bulletIndent=6, leading=14)
    add('Code', fontName='Courier', fontSize=9, textColor=colors.HexColor('#1e293b'), backColor=colors.HexColor('#f1f5f9'), spaceAfter=4, leading=13, leftIndent=10)
    add('Footer', fontName='Helvetica', fontSize=8, textColor=GRAY, alignment=TA_CENTER)
    return s

def tbl(data, col_widths=None):
    t = Table(data, colWidths=col_widths, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), ORANGE),
        ('TEXTCOLOR', (0,0), (-1,0), WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (1,1), (-1,-1), 'Helvetica'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, colors.HexColor('#f8fafc')]),
        ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    return t

def cover_page(story, s, title, subtitle):
    story.append(Spacer(1, 3*cm))
    # orange banner
    banner = Table([[Paragraph(title, s['TitlePage'])]], colWidths=[W - 4*cm])
    banner.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),ORANGE),('TOPPADDING',(0,0),(-1,-1),18),('BOTTOMPADDING',(0,0),(-1,-1),18),('LEFTPADDING',(0,0),(-1,-1),20)]))
    story.append(banner)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(subtitle, s['SubTitle']))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width='100%', thickness=1, color=ORANGE))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph('FinClaw — AI-Assisted Paper Trading Dashboard', s['Footer']))
    story.append(PageBreak())

def h1(story, s, text):
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(text, s['H1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=ORANGE))
    story.append(Spacer(1, 0.15*cm))

def h2(story, s, text):
    story.append(Paragraph(text, s['H2']))

def body(story, s, text):
    story.append(Paragraph(text, s['Body']))

def bullet(story, s, items):
    for item in items:
        story.append(Paragraph(f'• {item}', s['Bullet']))

def code(story, s, lines):
    for line in lines:
        story.append(Paragraph(line.replace(' ', '&nbsp;').replace('<','&lt;').replace('>','&gt;'), s['Code']))

def make_doc(path, title):
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm, title=title)
    return doc

# ─────────────────────────────────────────────
# PDF 1 — Tech Stack & Architecture
# ─────────────────────────────────────────────
def pdf_tech_stack():
    s = base_styles()
    story = []
    cover_page(story, s, 'Tech Stack &\nArchitecture', 'FinClaw System Design Reference')

    h1(story, s, '1. Project Overview')
    body(story, s, 'FinClaw is a lightweight AI-assisted paper-trading dashboard. Users onboard, set risk policies, view portfolio summaries, chat with an AI assistant, and submit guarded trade intents — all backed by a FastAPI service that optionally connects to Alpaca\'s paper-trading API.')

    h1(story, s, '2. High-Level Architecture')
    code(story, s, [
        'BROWSER',
        '  login.html  ──►  index.html (React 18 UMD + Recharts)',
        '                        │',
        '                   api.js (fetch wrapper)',
        '                        │ HTTP / JSON',
        '  FastAPI Backend (main.py)',
        '     ├── services.py   business logic',
        '     ├── models.py     SQLAlchemy ORM',
        '     ├── schemas.py    Pydantic validation',
        '     ├── security.py   bcrypt hashing',
        '     ├── config.py     pydantic-settings / .env',
        '     ├── automation.py background agent thread',
        '     └── alpaca_client.py  paper-trade broker',
        '                        │',
        '                   SQLite (finclaw.db)',
        '                        │ optional',
        '              Alpaca Paper Trading API',
    ])

    h1(story, s, '3. Layer Breakdown')
    story.append(tbl([
        ['Layer','Technology','Role'],
        ['UI','HTML + Tailwind CDN + React 18 UMD + Recharts','Dashboard, forms, charts'],
        ['API Client','api.js (fetch)','Browser ↔ Backend bridge'],
        ['Backend','FastAPI + Uvicorn','REST API, routing, validation'],
        ['ORM','SQLAlchemy 2','Database access layer'],
        ['Database','SQLite','Persistent local storage'],
        ['Validation','Pydantic v2','Request/response schemas'],
        ['Auth','passlib bcrypt','Password hashing'],
        ['Broker','Alpaca SDK (optional)','Paper-trade execution'],
        ['Agent','Python threading','Autonomous trading loop'],
        ['Container','Docker + docker-compose','Local deployment'],
    ], col_widths=[3.5*cm, 6*cm, 7*cm]))

    h1(story, s, '4. Backend Modules')
    story.append(tbl([
        ['File','Responsibility'],
        ['main.py','FastAPI app, all routes, CORS, global error handler, lifespan'],
        ['services.py','Auth, policies, portfolio, chat, trade validation, audit'],
        ['models.py','SQLAlchemy ORM: User, Policy, Trade, AuditLog'],
        ['schemas.py','Pydantic request/response models with field-level validation'],
        ['config.py','Settings class, .env loading, approved tickers list'],
        ['security.py','hash_password / verify_password via passlib bcrypt'],
        ['database.py','Engine, SessionLocal, Base, get_db dependency'],
        ['automation.py','TradingAutomationAgent — threaded loop, state management'],
        ['alpaca_client.py','Real Alpaca SDK call or simulated fallback'],
        ['logging_config.py','Structured JSON logging setup'],
    ], col_widths=[4*cm, 12.5*cm]))

    h1(story, s, '5. Data Models')
    story.append(tbl([
        ['Model','Key Fields'],
        ['User','id, email, password, goal, risk, experience, asset, created_at'],
        ['Policy','id, user_email, title, value, enabled'],
        ['Trade','id, user_email, asset, trade_type, amount, quantity, pnl_percent, status, auto_ai, execution_reason, created_at'],
        ['AuditLog','id, user_email, action, decision, reason, payload, created_at'],
    ], col_widths=[3.5*cm, 13*cm]))

    h1(story, s, '6. Tech Stack Summary')
    story.append(tbl([
        ['Category','Choice','Notes'],
        ['Language','Python 3.11+',''],
        ['Web Framework','FastAPI','Auto OpenAPI docs'],
        ['ASGI Server','Uvicorn','--reload for dev'],
        ['ORM','SQLAlchemy 2','mapped_column style'],
        ['Validation','Pydantic v2','field_validator support'],
        ['Settings','pydantic-settings','.env file loading'],
        ['Auth','passlib[bcrypt]','hash + verify'],
        ['Database','SQLite','finclaw.db'],
        ['Broker SDK','alpaca-trade-api','Optional; simulated fallback'],
        ['Frontend','React 18 UMD','No build step, CDN'],
        ['Styling','Tailwind CSS CDN','JIT via CDN'],
        ['Charts','Recharts 2 UMD','AreaChart, PieChart'],
        ['JSX','Babel Standalone','In-browser transpile'],
        ['Container','Docker + Compose','Multi-service local stack'],
        ['Testing','pytest + TestClient','backend/tests/test_api.py'],
    ], col_widths=[4*cm, 5*cm, 7.5*cm]))

    make_doc('Tech-Stack-and-Architecture.pdf', 'Tech Stack & Architecture').build(story)
    print('Done: Tech-Stack-and-Architecture.pdf')

# ─────────────────────────────────────────────
# PDF 2 — Deployment Guide
# ─────────────────────────────────────────────
def pdf_deployment():
    s = base_styles()
    story = []
    cover_page(story, s, 'Deployment Guide', 'Local, Docker & Cloud Deployment Reference')

    h1(story, s, '1. Project Overview')
    body(story, s, 'This guide covers all deployment paths for FinClaw: local development setup, Docker Compose for containerised local deployment, and cloud platform options for staging/production.')

    h1(story, s, '2. Prerequisites')
    bullet(story, s, [
        'Python 3.11+',
        'Node.js / npm (optional, for frontend dev server)',
        'Docker + Docker Compose (for containerised deployment)',
        'Git',
        'Alpaca paper trading account (optional)',
    ])

    h1(story, s, '3. Local Setup — Backend')
    code(story, s, [
        'cd backend',
        'python -m venv .venv',
        '.venv\\Scripts\\activate',
        'pip install -r requirements.txt',
        'copy .env.example .env',
        '# Edit .env with your values',
        'python seed.py',
        'uvicorn app.main:app --reload --host 127.0.0.1 --port 8000',
    ])

    h1(story, s, '4. Local Setup — Frontend')
    code(story, s, [
        'cd frontend',
        'python -m http.server 3000',
        '# OR',
        'npm run start',
    ])
    body(story, s, 'Open: http://127.0.0.1:3000/login.html')

    h1(story, s, '5. Docker Compose Deployment')
    code(story, s, [
        'cd "ai trading"',
        'docker compose up --build',
    ])
    story.append(tbl([
        ['Service','Port','Description'],
        ['backend','8000','FastAPI + Uvicorn'],
        ['frontend','3000','Static file server'],
    ], col_widths=[4*cm, 3*cm, 9.5*cm]))
    story.append(Spacer(1, 0.3*cm))
    code(story, s, [
        '# Stop',
        'docker compose down',
        '# Stop and remove volumes',
        'docker compose down -v',
    ])

    h1(story, s, '6. Environment Variables')
    story.append(tbl([
        ['Variable','Default','Description'],
        ['APP_NAME','FinClaw API','Application name'],
        ['APP_ENV','development','Environment tag'],
        ['DATABASE_URL','sqlite:///./finclaw.db','DB connection string'],
        ['CORS_ORIGINS','*','Allowed CORS origins'],
        ['ALPACA_API_KEY','(empty)','Alpaca key (optional)'],
        ['ALPACA_SECRET_KEY','(empty)','Alpaca secret (optional)'],
        ['ALPACA_PAPER','true','Use paper trading'],
        ['DEFAULT_CASH_LIMIT','500','Max daily spend'],
        ['DEFAULT_MAX_ORDER_NOTIONAL','100','Max single order USD'],
        ['DEFAULT_MAX_DAILY_TRADES','3','Max trades per day'],
        ['DEFAULT_APPROVED_TICKERS','AAPL,MSFT,NVDA,GOOGL,BTCUSD,ETHUSD','Allowed tickers'],
    ], col_widths=[5.5*cm, 4*cm, 7*cm]))

    h1(story, s, '7. Cloud Deployment Options')
    story.append(tbl([
        ['Platform','Method'],
        ['AWS App Runner','Deploy backend/ as Python web service; run uvicorn app.main:app --host 0.0.0.0 --port 8000'],
        ['Render / Railway','Same as App Runner; set env vars in dashboard'],
        ['Fly.io','fly launch from backend/; set secrets via fly secrets set'],
        ['Netlify / Vercel','Serve frontend/ as static files; backend must run separately'],
    ], col_widths=[4.5*cm, 12*cm]))

    h1(story, s, '8. Production Checklist')
    bullet(story, s, [
        'Replace SQLite with PostgreSQL — set DATABASE_URL accordingly',
        'Restrict CORS_ORIGINS to your frontend domain',
        'Set real ALPACA_API_KEY and ALPACA_SECRET_KEY as environment secrets only',
        'Put frontend behind a CDN (CloudFront, Cloudflare)',
        'Add JWT/session auth before handling real users',
        'Enable HTTPS on all endpoints',
        'Set APP_ENV=production',
    ])

    h1(story, s, '9. Health Check')
    code(story, s, [
        'GET http://127.0.0.1:8000/health',
        '',
        'Response: {"ok": true, "app": "FinClaw API", "env": "development"}',
    ])

    h1(story, s, '10. URLs Reference')
    story.append(tbl([
        ['Resource','URL'],
        ['Frontend','http://127.0.0.1:3000/login.html'],
        ['Backend API','http://127.0.0.1:8000'],
        ['Swagger Docs','http://127.0.0.1:8000/docs'],
        ['Health Check','http://127.0.0.1:8000/health'],
    ], col_widths=[4*cm, 12.5*cm]))

    make_doc('Deployment-Guide.pdf', 'Deployment Guide').build(story)
    print('Done: Deployment-Guide.pdf')

# ─────────────────────────────────────────────
# PDF 3 — How To Use
# ─────────────────────────────────────────────
def pdf_how_to_use():
    s = base_styles()
    story = []
    cover_page(story, s, 'How To Use', 'User Guide & API Usage Reference')

    h1(story, s, '1. Project Overview')
    body(story, s, 'FinClaw provides a browser-based dashboard for AI-assisted paper trading. This guide explains how to register, navigate the UI, interact with the AI agent, submit trade intents, and use the API directly.')

    h1(story, s, '2. Getting Started')
    h2(story, s, 'Step 1 — Open the app')
    body(story, s, 'Navigate to: http://127.0.0.1:3000/login.html')

    h2(story, s, 'Step 2 — Register (Onboarding)')
    bullet(story, s, [
        'Enter your email and a password (min 8 characters)',
        'Select your investment goal (e.g. growth)',
        'Select experience level (e.g. novice)',
        'Select risk tolerance (e.g. medium)',
        'Select asset class (e.g. stocks)',
        'Click Onboard',
    ])

    h2(story, s, 'Step 3 — Log In')
    body(story, s, 'Enter your email and password, click Login. You are redirected to the dashboard.')

    h1(story, s, '3. Dashboard Navigation')
    story.append(tbl([
        ['Section','What It Shows'],
        ['Dashboard','Balance, market status, agent action widget, portfolio chart, recent trades, safety policies'],
        ['Portfolio','All holdings with shares, value, and daily change %'],
        ['Trade History','Full trade log with asset, type, amount, date, AI flag'],
        ['Settings','Automation level, notifications, theme'],
    ], col_widths=[4*cm, 12.5*cm]))

    h1(story, s, '4. Key UI Features')
    h2(story, s, 'Beginner Mode')
    body(story, s, 'Toggle in the sidebar footer. When ON: tooltips appear on hover, plain-language explanations are shown throughout the dashboard.')

    h2(story, s, 'Agent Action Widget')
    bullet(story, s, [
        'Shows the AI agent\'s current suggested trade',
        'Click "Allow Buy" to approve or "Reject" to block',
        'Status updates to confirmed or rejected state',
    ])

    h2(story, s, 'Agent Instructions Panel')
    bullet(story, s, [
        'Lists all active trading rules the agent follows',
        'Type a new rule in the input box and click "Add Rule"',
        'Rules are saved to localStorage',
    ])

    h2(story, s, 'AI Chat Assistant')
    bullet(story, s, [
        'Click the orange bot button (bottom-right corner)',
        'Type any question about your portfolio or trades',
        'Use quick suggestion buttons for common queries',
        'Chat calls POST /api/chat and falls back to static responses if API is unavailable',
    ])

    h1(story, s, '5. API Usage')
    h2(story, s, 'Authentication')
    code(story, s, [
        'POST /api/auth/onboarding',
        '{"email":"user@example.com","password":"secret123",',
        ' "goal":"growth","experience":"novice","risk":"medium","asset":"stocks"}',
        '',
        'POST /api/auth/login',
        '{"email":"user@example.com","password":"secret123"}',
    ])

    h2(story, s, 'Submit a Trade Intent')
    code(story, s, [
        'POST /api/trade-intents',
        '{',
        '  "user_email": "user@example.com",',
        '  "ticker": "AAPL",',
        '  "side": "buy",',
        '  "notional_usd": 50.0,',
        '  "reason": "Momentum signal detected",',
        '  "source": "frontend"',
        '}',
    ])

    h2(story, s, 'AI Chat')
    code(story, s, [
        'POST /api/chat',
        '{"message": "How is my portfolio performing?"}',
        '',
        'Response: {"ok": true, "reply": "Your portfolio is up today..."}',
    ])

    h2(story, s, 'Automation Agent')
    code(story, s, [
        'POST /api/agent/configure',
        '{"user_email":"agent@trading.ai","tickers":["AAPL","NVDA"],"loop_interval_seconds":30}',
        '',
        'POST /api/agent/start',
        'POST /api/agent/stop',
        'POST /api/agent/run-once',
        'GET  /api/agent/status',
    ])

    h1(story, s, '6. Trade Validation Rules')
    story.append(tbl([
        ['Rule','Value (default)'],
        ['Approved tickers','AAPL, MSFT, NVDA, GOOGL, BTCUSD, ETHUSD'],
        ['Max order notional','$100 USD'],
        ['Max daily trades','3 per user'],
    ], col_widths=[6*cm, 10.5*cm]))

    h1(story, s, '7. Inputs & Outputs Summary')
    story.append(tbl([
        ['Endpoint','Input','Output'],
        ['/api/auth/login','email, password','user profile object'],
        ['/api/dashboard/{email}','email (path)','balance, holdings, trades'],
        ['/api/trade-intents','ticker, side, notional_usd','trade_id, broker_result, reason'],
        ['/api/chat','message string','reply string'],
        ['/api/agent/status','none','agent state + last 20 logs'],
    ], col_widths=[5*cm, 5*cm, 6.5*cm]))

    make_doc('How-To-Use.pdf', 'How To Use').build(story)
    print('Done: How-To-Use.pdf')

# ─────────────────────────────────────────────
# PDF 4 — Network Fix & Redeployment Report
# ─────────────────────────────────────────────
def pdf_fixes():
    s = base_styles()
    story = []
    cover_page(story, s, 'Network Fix &\nRedeployment Report', 'Issues, Fixes & Verification Log')

    h1(story, s, '1. Project Overview')
    body(story, s, 'This report documents all known issues found in the original FinClaw codebase, the fixes applied, verification steps taken, and remaining limitations.')

    h1(story, s, '2. Issues Found & Fixes Applied')
    story.append(tbl([
        ['#','Issue','Severity','Fix Applied'],
        ['1','Plaintext passwords stored in database','Critical','Added bcrypt hashing in security.py; legacy plain passwords auto-migrated on next login'],
        ['2','Real-looking secrets in .env.example','High','Replaced all values with empty placeholders'],
        ['3','No input validation on any endpoint','High','Pydantic v2 schemas with field constraints on all request bodies'],
        ['4','Unhandled exceptions returned raw 500 errors','Medium','Global exception_handler returns structured JSON {"ok":false,"detail":"..."}'],
        ['5','No audit trail for trade decisions','Medium','AuditLog table records every trade intent with decision and reason'],
        ['6','Alpaca SDK import crash if not installed','Medium','Try/except import block; graceful simulated fallback mode'],
        ['7','CORS set to wildcard *','Low','Configurable via CORS_ORIGINS env var; wildcard only in dev'],
        ['8','No .gitignore for sensitive files','Low','Added rules for .env, *.db, __pycache__, .venv'],
        ['9','Portfolio data fully mocked','Info','Documented as demo limitation; real broker integration is optional'],
        ['10','Chat AI uses keyword matching only','Info','Documented; LLM integration left as future improvement'],
    ], col_widths=[0.6*cm, 4.8*cm, 2*cm, 9.1*cm]))

    h1(story, s, '3. Security Improvements Detail')
    h2(story, s, '3.1 Password Hashing')
    code(story, s, [
        '# security.py',
        'from passlib.context import CryptContext',
        'pwd_context = CryptContext(schemes=["bcrypt"])',
        '',
        'def hash_password(plain: str) -> str:',
        '    return pwd_context.hash(plain)',
        '',
        'def verify_password(plain: str, hashed: str) -> bool:',
        '    return pwd_context.verify(plain, hashed)',
    ])

    h2(story, s, '3.2 Input Validation Example')
    code(story, s, [
        '# schemas.py',
        'class TradeIntent(BaseModel):',
        '    ticker: str = Field(min_length=1, max_length=20)',
        '    side: str  # validated to "buy" or "sell" only',
        '    notional_usd: float = Field(gt=0, le=1_000_000)',
        '',
        '    @field_validator("side")',
        '    def validate_side(cls, v):',
        '        if v.strip().lower() not in {"buy","sell"}:',
        '            raise ValueError("side must be buy or sell")',
        '        return v.strip().lower()',
    ])

    h2(story, s, '3.3 Global Error Handler')
    code(story, s, [
        '# main.py',
        '@app.exception_handler(Exception)',
        'async def unhandled_exception_handler(request, exc):',
        '    logger.exception("Unhandled error for %s %s", request.method, request.url.path)',
        '    return JSONResponse(status_code=500,',
        '        content={"ok": False, "detail": "Internal server error"})',
    ])

    h1(story, s, '4. Verification Steps')
    story.append(tbl([
        ['Test','Command / Action','Expected Result'],
        ['Health check','GET /health','{"ok":true,"app":"FinClaw API"}'],
        ['Onboarding','POST /api/auth/onboarding with valid payload','{"ok":true,"user":{...}}'],
        ['Login valid','POST /api/auth/login correct credentials','{"ok":true,"user":{...}}'],
        ['Login invalid','POST /api/auth/login wrong password','HTTP 401'],
        ['Trade allowed','POST /api/trade-intents AAPL $50','{"ok":true,"trade_id":...}'],
        ['Trade blocked — bad ticker','POST /api/trade-intents XYZ $50','HTTP 403 ticker not approved'],
        ['Trade blocked — over limit','POST /api/trade-intents AAPL $200','HTTP 403 exceeds max notional'],
        ['Daily limit','4th trade same day','HTTP 403 daily limit reached'],
        ['Pytest suite','cd backend && pytest','All tests pass'],
        ['Agent run-once','POST /api/agent/run-once','Cycle executes, trade logged'],
    ], col_widths=[4*cm, 5.5*cm, 7*cm]))

    h1(story, s, '5. Redeployment Steps After Fix')
    code(story, s, [
        '# 1. Pull latest code',
        'git pull',
        '',
        '# 2. Reinstall dependencies',
        'pip install -r requirements.txt',
        '',
        '# 3. Reset database (if schema changed)',
        'del finclaw.db',
        'python seed.py',
        '',
        '# 4. Restart server',
        'uvicorn app.main:app --reload --host 127.0.0.1 --port 8000',
        '',
        '# 5. Run tests',
        'pytest',
    ])

    h1(story, s, '6. Remaining Limitations')
    story.append(tbl([
        ['Area','Limitation','Recommended Fix'],
        ['Auth','No JWT or session tokens','Implement OAuth2 + JWT'],
        ['Auth','No CSRF protection','Add CSRF middleware for production'],
        ['Database','SQLite not concurrent-safe','Migrate to PostgreSQL'],
        ['Portfolio','Mocked balance and holdings','Connect to real broker account API'],
        ['Chat AI','Keyword matching only','Integrate LLM (e.g. Amazon Bedrock)'],
        ['Frontend','CDN-based, no bundler','Use Vite or Next.js for production'],
        ['Observability','Basic logging only','Add CloudWatch / Datadog / Sentry'],
    ], col_widths=[3*cm, 5.5*cm, 8*cm]))

    h1(story, s, '7. Conclusion')
    body(story, s, 'The fixes applied bring FinClaw to a safe, runnable demo/staging state. Password security, input validation, error handling, and audit logging are all in place. The system is deployment-ready for demo use but requires another round of work — covering JWT auth, PostgreSQL, real broker integration, and observability — before handling real-money users in production.')

    make_doc('Network-Fix-and-Redeployment-Report.pdf', 'Network Fix & Redeployment Report').build(story)
    print('Done: Network-Fix-and-Redeployment-Report.pdf')

# ─────────────────────────────────────────────
# Run all
# ─────────────────────────────────────────────
if __name__ == '__main__':
    pdf_tech_stack()
    pdf_deployment()
    pdf_how_to_use()
    pdf_fixes()
    print('All 4 PDFs generated in docs/')
