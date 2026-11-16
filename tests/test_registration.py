from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.routers import registration as reg
from backend.routers.auth import get_current_account
from backend.security import verify_password

client = TestClient(app)

def payload(**changes):
    data = dict(token="registration-secret", full_name="Test Person", password="StrongPass123", cpf="52998224725", birth_date="2000-01-01", phone=None, address="Test street 123", plan_id=1, payment={"type":"boleto"})
    data.update(changes)
    return data

@pytest.fixture
def database(monkeypatch):
    cursor=MagicMock()
    connection=MagicMock()
    connection.cursor.return_value.__enter__.return_value=cursor
    @contextmanager
    def connect():
        yield connection
    monkeypatch.setattr(reg,"get_db_connection",connect)
    return cursor

@pytest.mark.parametrize("changes", [{"cpf":"11111111111"},{"cpf":"52998224726"},{"password":"abcdefghijk"},{"full_name":"Test"},{"address":""},{"birth_date":"2999-01-01"}])
def test_invalid_details_rejected_before_database(changes):
    assert client.post("/api/registration/complete",json=payload(**changes)).status_code==422

def test_optional_phone_and_valid_cpf():
    assert reg.validate_details(reg.Complete(**payload()))=="52998224725"

def test_start_delivers_only_to_local_outbox(database,monkeypatch,tmp_path):
    monkeypatch.setattr(reg,"OUTBOX",tmp_path)
    database.fetchone.return_value=None
    response=client.post("/api/registration/start",json={"email":" Test@Example.com "})
    assert response.status_code==200
    result=response.json()
    assert "code" not in result
    message=json.loads(next(tmp_path.iterdir()).read_text())
    assert message["to"]=="test@example.com"
    assert len(message["body"].split()[-1])==6

def test_invalid_code_consumes_attempt(database):
    database.fetchone.return_value=(reg.digest("other"),)
    assert client.post("/api/registration/verify",json={"token":"token","code":"123456"}).status_code==400
    assert "attempts=attempts+1" in database.execute.call_args.args[0]

def test_valid_code(database):
    database.fetchone.return_value=(reg.digest("token123456"),)
    assert client.post("/api/registration/verify",json={"token":"token","code":"123456"}).status_code==200

def test_completion_requires_verified_live_session(database):
    database.fetchone.return_value=None
    assert client.post("/api/registration/complete",json=payload()).status_code==401
    assert database.execute.call_count==1

def test_completion_persists_hash_and_consumes_session(database,monkeypatch,tmp_path):
    monkeypatch.setattr(reg,"OUTBOX",tmp_path)
    database.fetchone.side_effect=[("test@example.com",None),(1,),(42,),(13,)]
    response=client.post("/api/registration/complete",json=payload())
    assert response.status_code==201
    assert response.json()["id"]==42
    inserts=[call.args for call in database.execute.call_args_list if "INSERT INTO public.account(" in call.args[0]]
    assert verify_password("StrongPass123",inserts[0][1][1])
    assert "DELETE FROM public.registration_session" in database.execute.call_args.args[0]
    assert len(list(tmp_path.iterdir()))==1

@pytest.mark.parametrize("method,url,data",[("put","/api/accounts/7/plan",{"plan_id":1}),("post","/api/accounts/7/payment-methods",{"type":"boleto"})])
def test_account_mutations_require_owner(method,url,data):
    assert getattr(client,method)(url,json=data).status_code==401
    app.dependency_overrides[get_current_account]=lambda:SimpleNamespace(id=8)
    try:
        assert getattr(client,method)(url,json=data).status_code==403
    finally:
        app.dependency_overrides.clear()

def test_google_disabled_without_configuration(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID",raising=False)
    assert client.post("/api/registration/google",json={"credential":"fake"}).status_code==503


def test_google_rejects_invalid_identity(monkeypatch):
    from google.oauth2 import id_token
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    def invalid(*args):
        raise ValueError("Invalid signature")
    monkeypatch.setattr(id_token, "verify_oauth2_token", invalid)
    assert client.post("/api/registration/google", json={"credential":"bad"}).status_code == 401


def test_google_creates_verified_session_for_verified_identity(database, monkeypatch):
    from google.oauth2 import id_token
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    def identity(credential, transport, audience):
        assert audience == "client-id"
        return {"sub":"google-user-id", "email":"user@example.com", "email_verified":True}
    monkeypatch.setattr(id_token, "verify_oauth2_token", identity)
    database.fetchone.side_effect = [None, None]
    response = client.post("/api/registration/google", json={"credential":"verified-by-mock"})
    assert response.status_code == 200
    assert response.json()["verified"] is True
    assert database.execute.call_args.args[1][-1] == "google-user-id"
