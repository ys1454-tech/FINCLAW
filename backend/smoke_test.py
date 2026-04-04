from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print(client.get('/health').status_code)
print(client.get('/health').json())
