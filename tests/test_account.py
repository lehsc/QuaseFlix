from fastapi.testclient import TestClient
from backend.main import app

def test_legacy_registration_cannot_bypass_verification():
    assert TestClient(app).post("/api/accounts/", json={}).status_code == 410
