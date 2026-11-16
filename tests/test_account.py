import pytest
import uuid
import random
from fastapi.testclient import TestClient
from http import HTTPStatus
from backend.main import app
from backend.database.connection import get_db_connection
from backend.routers import accounts
from backend.security import verify_password

# Create a test client using FastAPI app object
client = TestClient(app)

@pytest.fixture
def account_payload():
    # Generate a unique 11-digit numeric string for CPF
    random_cpf = "".join([str(random.randint(0, 9)) for _ in range(11)])
    
    return {
        "email": f"user_{uuid.uuid4().hex[:8]}@quaseflix-test.com",
        "password": "Senha@12345",
        "cpf": random_cpf,
        "birth_date": "2000-05-15",
        "phone": "31999998888",
        "address": "Avenida Antonio Carlos, 6627",
    }


def test_register_account_success(account_payload):
    # Send a POST request to registration endpoint
    response = client.post("/api/accounts/", json = account_payload)

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["message"] == "Account registered successfully!"
    assert data["email"] == account_payload["email"]
    assert isinstance(data["id"], int)

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

    response = client.post("/api/accounts/", json = account_payload)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Unable to register account."}


def test_register_account_stores_only_a_hash_of_the_password(account_payload):
    response = client.post("/api/accounts/", json = account_payload)

    try:
        assert response.status_code == HTTPStatus.CREATED
        assert account_payload["password"] not in response.text

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT password_hash FROM public.account WHERE email = %s",
                    (account_payload["email"],)
                )
                stored_hash = cursor.fetchone()[0]

        assert stored_hash != account_payload["password"]
        assert account_payload["password"] not in stored_hash
        assert verify_password(account_payload["password"], stored_hash)
    finally:
        # Unlike the account_id fixture, this test creates the account itself.
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM public.account WHERE email = %s",
                    (account_payload["email"],)
                )


@pytest.mark.parametrize("password", ["12345", "x" * 129])
def test_register_account_rejects_invalid_password_length(account_payload, password):
    account_payload["password"] = password

    response = client.post("/api/accounts/", json = account_payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM public.account WHERE email = %s",
                (account_payload["email"],)
            )
            assert cursor.fetchone()[0] == 0


def test_register_account_requires_a_password(account_payload):
    del account_payload["password"]

    response = client.post("/api/accounts/", json = account_payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("phone", [None, "", "31999998888"])
def test_register_account_accepts_optional_phone(account_payload, monkeypatch, phone):
    account_payload["phone"] = phone
    saved_accounts = []

    def save(account):
        saved_accounts.append(account)
        return 123

    monkeypatch.setattr(accounts, "service_register_account", save)
    response = client.post("/api/accounts/", json=account_payload)

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["id"] == 123
    assert saved_accounts[0].phone == phone


def test_register_account_accepts_omitted_phone(account_payload, monkeypatch):
    del account_payload["phone"]
    saved_accounts = []

    def save(account):
        saved_accounts.append(account)
        return 123

    monkeypatch.setattr(accounts, "service_register_account", save)
    response = client.post("/api/accounts/", json=account_payload)

    assert response.status_code == HTTPStatus.CREATED
    assert saved_accounts[0].phone is None
