from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print('login', client.post('/api/auth/login', json={'email':'test@example.com','password':'secret123'}).status_code)
print('onboarding', client.post('/api/auth/onboarding', json={'email':'new@example.com','password':'secret123','goal':'growth','experience':'novice','risk':'medium','asset':'stocks'}).status_code)
print('chat', client.post('/api/chat', json={'message':'How is my trade performing?','email':'test@example.com'}).status_code)
print('policies', client.post('/api/policies', json={'email':'test@example.com','policies':[{'title':'Daily Trade Limit','value':'Max trade limit $100 per transaction','enabled':True}]}).status_code)
print('fetch_policies', client.get('/api/policies/test@example.com').status_code)
print('dashboard', client.get('/api/dashboard/test@example.com').status_code)
print('trades', client.get('/api/trades/test@example.com').status_code)
print('intent_allowed', client.post('/api/trade-intents', json={'user_email':'test@example.com','ticker':'AAPL','side':'buy','notional_usd':50,'quantity':1,'reason':'test'}).status_code)
print('intent_blocked', client.post('/api/trade-intents', json={'user_email':'test@example.com','ticker':'TSLA','side':'buy','notional_usd':50,'quantity':1,'reason':'test'}).status_code)
