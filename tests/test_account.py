import pytest
from fastapi.testclient import TestClient
from http import HTTPStatus
from backend.main import app
from backend.database.connection import get_db_connection
from backend.routers import accounts

# Create a test client using FastAPI app object
client = TestClient(app)

@pytest.fixture
def account_payload():
    return {
        "email": "leticia@ufmg.br",
        "password_hash": "securehashedpassword123",
        "cpf": "14514514504",
        "birth_date": "2000-05-15",
        "phone": "31999998888",
        "address": "Avenida Antonio Carlos, 6627",
    }


def test_register_account_success(account_payload):
    # Send a POST request to registration endpoint
    response = client.post("/api/accounts/", json=account_payload)

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["message"] == "Account registered successfully!"
    assert data["email"] == account_payload["email"]

    # A separate connection verifies that the account was committed.
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT email, cpf FROM public.account WHERE email = %s",
                (account_payload["email"],)
            )
            assert cursor.fetchone() == (
                account_payload["email"], account_payload["cpf"]
            )


def test_register_account_failure(account_payload, monkeypatch):
    monkeypatch.setattr(accounts, "service_register_account", lambda account: False)

    response = client.post("/api/accounts/", json=account_payload)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Unable to register account."}