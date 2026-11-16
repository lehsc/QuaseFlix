"""
Integration tests for the payment method endpoints.

Like tests/test_account.py they use the real PostgreSQL database
(see the README). Every test registers its own account (account_id fixture in
conftest.py) and deletes it at the end; ON DELETE CASCADE also removes the
payment methods created for it.
"""
from datetime import date
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import get_db_connection
from backend.main import app
from backend.routers import payment_methods

client = TestClient(app)

CARD_NUMBER = "4111111111111111"  # well-known test number (passes Luhn)
NON_EXISTENT_ACCOUNT_ID = 2_147_483_647  # largest value of an integer column


@pytest.fixture
def credit_card_payload():
    return {
        "type": "credit_card",
        "card_number": CARD_NUMBER,
        "holder_name": "Maria da Silva",
        "cvc": "123",
        "expiration_month": 12,
        "expiration_year": date.today().year + 3,
        "bank_name": "Banco Exemplo",
    }


def url_for(account_id: int) -> str:
    return f"/api/accounts/{account_id}/payment-methods"


def count_payment_methods(account_id: int) -> int:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM public.payment_method WHERE account_id = %s",
                (account_id,)
            )
            return cursor.fetchone()[0]


def test_register_credit_card_success(account_id, credit_card_payload):
    response = client.post(url_for(account_id), json = credit_card_payload)

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["message"] == "Payment method registered successfully!"
    assert data["type"] == "credit_card"
    assert data["last_four"] == "1111"
    assert data["holder_name"] == "Maria da Silva"

    # The sensitive data must never come back in the response.
    assert CARD_NUMBER not in response.text
    assert "cvc" not in data

    # A separate connection verifies what was committed.
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT pm.account_id, pm.type, cc.card_number, cc.holder_name,
                       cc.expiration_date, cc.bank_name
                FROM public.payment_method pm
                JOIN public.credit_card_details cc ON cc.payment_method_id = pm.id
                WHERE pm.id = %s
                """,
                (data["id"],)
            )
            assert cursor.fetchone() == (
                account_id,
                "credit_card",
                "************1111",  # only the masked number is stored
                "Maria da Silva",
                date(credit_card_payload["expiration_year"], 12, 31),
                "Banco Exemplo",
            )


def test_register_credit_card_without_bank_name(account_id, credit_card_payload):
    del credit_card_payload["bank_name"]

    response = client.post(url_for(account_id), json = credit_card_payload)

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["bank_name"] is None


def test_register_boleto_success(account_id):
    response = client.post(url_for(account_id), json = {"type": "boleto"})

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["type"] == "boleto"
    assert len(data["barcode"]) == 47 and data["barcode"].isdigit()
    assert date.fromisoformat(data["due_date"]) > date.today()

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT pm.account_id, pm.type, bd.barcode, bd.due_date
                FROM public.payment_method pm
                JOIN public.boleto_details bd ON bd.payment_method_id = pm.id
                WHERE pm.id = %s
                """,
                (data["id"],)
            )
            assert cursor.fetchone() == (
                account_id,
                "boleto",
                data["barcode"],
                date.fromisoformat(data["due_date"]),
            )


def test_account_can_have_more_than_one_payment_method(account_id, credit_card_payload):
    first = client.post(url_for(account_id), json = credit_card_payload)
    second = client.post(url_for(account_id), json = {"type": "boleto"})

    assert first.status_code == HTTPStatus.CREATED
    assert second.status_code == HTTPStatus.CREATED
    assert first.json()["id"] != second.json()["id"]
    assert count_payment_methods(account_id) == 2


def test_register_card_with_invalid_number_is_rejected(account_id, credit_card_payload):
    credit_card_payload["card_number"] = "4111111111111112"  # fails Luhn

    response = client.post(url_for(account_id), json = credit_card_payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == {"detail": "Invalid card number."}
    assert count_payment_methods(account_id) == 0


def test_register_expired_card_is_rejected(account_id, credit_card_payload):
    credit_card_payload["expiration_year"] = date.today().year - 1

    response = client.post(url_for(account_id), json = credit_card_payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == {"detail": "Card is expired."}
    assert count_payment_methods(account_id) == 0


def test_register_card_with_invalid_cvc_is_rejected(account_id, credit_card_payload):
    credit_card_payload["cvc"] = "12"

    response = client.post(url_for(account_id), json = credit_card_payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert count_payment_methods(account_id) == 0


def test_register_card_with_missing_field_is_rejected(account_id, credit_card_payload):
    del credit_card_payload["cvc"]

    response = client.post(url_for(account_id), json = credit_card_payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert count_payment_methods(account_id) == 0


@pytest.mark.parametrize("payload", [{"type": "pix"}, {}])
def test_register_unknown_or_missing_type_is_rejected(account_id, payload):
    response = client.post(url_for(account_id), json = payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert count_payment_methods(account_id) == 0


def test_register_payment_method_for_unknown_account(credit_card_payload):
    response = client.post(url_for(NON_EXISTENT_ACCOUNT_ID), json = credit_card_payload)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": f"Account {NON_EXISTENT_ACCOUNT_ID} not found."}


def test_register_payment_method_failure(credit_card_payload, monkeypatch):
    def broken_service(payment_method):
        raise RuntimeError("database is down")

    monkeypatch.setattr(payment_methods, "service_register_payment_method", broken_service)

    response = client.post(url_for(1), json = credit_card_payload)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    # The internal error message must not reach the client.
    assert response.json() == {"detail": "Unable to register payment method."}


@pytest.fixture(autouse=True)
def authenticated_request():
    """These tests exercise services; ownership is tested in test_registration."""
    from fastapi import Request
    from types import SimpleNamespace
    from backend.routers.auth import get_current_account
    def owner(request: Request):
        return SimpleNamespace(id=int(request.path_params.get("account_id", 1)))
    app.dependency_overrides[get_current_account] = owner
    yield
    app.dependency_overrides.pop(get_current_account, None)
