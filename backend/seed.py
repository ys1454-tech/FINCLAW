from app.database import Base, engine, SessionLocal
from app.services import bootstrap_user, create_trade, replace_policies

Base.metadata.create_all(bind=engine)
db = SessionLocal()
bootstrap_user(db, 'agent@trading.ai', 'demo12345', goal='growth', experience='novice', risk='medium', asset='stocks')
replace_policies(db, 'agent@trading.ai', [
    {'title': 'Daily Trade Limit', 'value': 'Max trade limit $500 per transaction', 'enabled': True},
    {'title': 'Momentum Trading', 'value': 'Buy on high upward momentum', 'enabled': True},
    {'title': 'Sector Exposure', 'value': 'Restrict maximum exposure to 15% per sector', 'enabled': True},
])
create_trade(db, 'agent@trading.ai', 'AAPL', 'Buy', 1200, 2.5, 'Seed demo trade', True, 'filled', 4.2)
create_trade(db, 'agent@trading.ai', 'BTCUSD', 'Sell', 3400, 0.05, 'Seed demo trade', False, 'filled', 12.5)
create_trade(db, 'agent@trading.ai', 'NVDA', 'Buy', 850, 1.1, 'Seed demo trade', True, 'filled', -1.2)
db.close()
print('Seed complete')
