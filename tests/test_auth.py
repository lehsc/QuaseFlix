"""
Integration tests for the login endpoints.

Like tests/test_account.py they use the real PostgreSQL database (see the
README). Every test registers its own account (registered_account fixture in
conftest.py) and deletes it at the end.
"""
import time
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from backend import security
from backend.database.connection import get_db_connection
from backend.main import app
from backend.routers import auth
from backend.security import ACCESS_TOKEN_TTL_SECONDS, create_access_token, decode_access_token

client = TestClient(app)

LOGIN_URL = "/api/auth/login"
ME_URL = "/api/auth/me"
NON_EXISTENT_ACCOUNT_ID = 2_147_483_647  # largest value of an integer column

INVALID_CREDENTIALS = {"detail": "Invalid e-mail or password."}


def login(email: str, password: str):
    return client.post(LOGIN_URL, json = {"email": email, "password": password})


def log_in_as(account: dict) -> str:
    response = login(account["email"], account["password"])
    assert response.status_code == HTTPStatus.OK
    return response.json()["token"]


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def set_status(account_id: int, account_status: str) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE public.account SET status = %s::public.account_status WHERE id = %s",
                (account_status, account_id)
            )


def set_age_in_days(account_id: int, days: int) -> None:
    """Makes the account look like it was created `days` days ago."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE public.account SET created_at = LOCALTIMESTAMP - make_interval(days => %s) "
                "WHERE id = %s",
                (days, account_id)
            )


# -------------------------------------------------------------------- login

def test_login_success(registered_account):
    response = login(registered_account["email"], registered_account["password"])

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["message"] == "Login successful!"
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == ACCESS_TOKEN_TTL_SECONDS
    assert data["account"] == {
        "id": registered_account["id"],
        "email": registered_account["email"],
        "status": "trial",
        "plan_id": 1,
    }
    assert decode_access_token(data["token"]) == registered_account["id"]

    # Neither the password nor its hash may come back.
    assert registered_account["password"] not in response.text
    assert "password" not in data["account"]
    assert "password_hash" not in response.text


def test_login_ignores_case_and_spaces_around_the_email(registered_account):
    response = login(f"  {registered_account['email'].upper()}  ", registered_account["password"])

    assert response.status_code == HTTPStatus.OK
    assert response.json()["account"]["id"] == registered_account["id"]


@pytest.mark.parametrize("change", [
    lambda password: password.lower(),
    lambda password: password.upper(),
    lambda password: password[:-1],
    lambda password: password + "x",
    lambda password: " " + password,
])
def test_login_with_wrong_password(registered_account, change):
    response = login(registered_account["email"], change(registered_account["password"]))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == INVALID_CREDENTIALS


def test_login_with_unknown_email_looks_like_a_wrong_password(registered_account):
    unknown = login("nobody@quaseflix-test.com", registered_account["password"])
    wrong_password = login(registered_account["email"], "not-the-password")

    assert unknown.status_code == wrong_password.status_code == HTTPStatus.UNAUTHORIZED
    assert unknown.json() == wrong_password.json() == INVALID_CREDENTIALS


@pytest.mark.parametrize("payload", [
    {},
    {"email": "maria@example.com"},
    {"password": "Senha@12345"},
    {"email": "", "password": "Senha@12345"},
    {"email": "maria@example.com", "password": ""},
    {"email": "maria@example.com", "password": "x" * 129},
    {"email": None, "password": None},
])
def test_login_with_invalid_body(payload):
    response = client.post(LOGIN_URL, json = payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_login_with_an_account_whose_password_was_not_hashed(registered_account):
    # An account created before the passwords started to be hashed.
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE public.account SET password_hash = %s WHERE id = %s",
                (registered_account["password"], registered_account["id"])
            )

    response = login(registered_account["email"], registered_account["password"])

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == INVALID_CREDENTIALS


def test_login_canceled_account_is_refused(registered_account):
    set_status(registered_account["id"], "CANCELED")

    response = login(registered_account["email"], registered_account["password"])

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"detail": "This account has been canceled."}


def test_login_does_not_reveal_that_the_account_is_canceled_to_a_wrong_password(registered_account):
    set_status(registered_account["id"], "CANCELED")

    response = login(registered_account["email"], "not-the-password")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == INVALID_CREDENTIALS


def test_login_inside_the_trial_period(registered_account):
    set_age_in_days(registered_account["id"], 29)

    response = login(registered_account["email"], registered_account["password"])

    assert response.status_code == HTTPStatus.OK
    assert response.json()["account"]["status"] == "trial"


def test_login_after_the_trial_without_an_active_subscription_is_refused(registered_account):
    set_age_in_days(registered_account["id"], 31)

    response = login(registered_account["email"], registered_account["password"])

    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert response.json() == {
        "detail": "The free trial has ended and there is no active subscription."
    }


def test_login_active_account_after_the_trial(registered_account):
    set_status(registered_account["id"], "ACTIVE")
    set_age_in_days(registered_account["id"], 90)

    response = login(registered_account["email"], registered_account["password"])

    assert response.status_code == HTTPStatus.OK
    assert response.json()["account"]["status"] == "active"


def test_login_failure(monkeypatch):
    def broken_service(email, password):
        raise RuntimeError("database is down")

    monkeypatch.setattr(auth, "service_authenticate", broken_service)

    response = login("maria@example.com", "Senha@12345")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    # The internal error message must not reach the client.
    assert response.json() == {"detail": "Unable to log in."}


# ----------------------------------------------------------------------- me

def test_me_with_the_token_from_login(registered_account):
    token = log_in_as(registered_account)

    response = client.get(ME_URL, headers = bearer(token))

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "account": {
            "id": registered_account["id"],
            "email": registered_account["email"],
            "status": "trial",
            "plan_id": 1,
        }
    }


def test_me_without_a_token():
    response = client.get(ME_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"detail": "Authentication required."}
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_another_authorization_scheme():
    response = client.get(ME_URL, headers = {"Authorization": "Basic dXNlcjpwYXNz"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"detail": "Authentication required."}


@pytest.mark.parametrize("token", ["garbage", "a.b.c", "x.y"])
def test_me_with_a_malformed_token(token):
    response = client.get(ME_URL, headers = bearer(token))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"detail": "Invalid or expired token."}


def test_me_with_an_expired_token(registered_account):
    long_ago = time.time() - ACCESS_TOKEN_TTL_SECONDS - 60
    token = create_access_token(registered_account["id"], now = long_ago)

    response = client.get(ME_URL, headers = bearer(token))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"detail": "Invalid or expired token."}


def test_me_with_a_token_signed_with_another_key(registered_account, monkeypatch):
    token = log_in_as(registered_account)
    monkeypatch.setattr(security, "_SECRET_KEY", "another-key")

    response = client.get(ME_URL, headers = bearer(token))

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_me_with_a_token_of_an_account_that_does_not_exist():
    token = create_access_token(NON_EXISTENT_ACCOUNT_ID)

    response = client.get(ME_URL, headers = bearer(token))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"detail": "Invalid or expired token."}


def test_me_after_the_account_was_canceled(registered_account):
    token = log_in_as(registered_account)
    set_status(registered_account["id"], "CANCELED")

    response = client.get(ME_URL, headers = bearer(token))

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"detail": "This account has been canceled."}


def test_me_after_the_trial_ended(registered_account):
    token = log_in_as(registered_account)
    set_age_in_days(registered_account["id"], 31)

    response = client.get(ME_URL, headers = bearer(token))

    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED


def test_me_failure(monkeypatch):
    def broken_service(account_id):
        raise RuntimeError("database is down")

    monkeypatch.setattr(auth, "service_get_account_for_access", broken_service)

    response = client.get(ME_URL, headers = bearer(create_access_token(1)))

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Unable to validate the session."}


# --------------------------------------------------------------------- CORS

def test_browser_may_send_the_authorization_header():
    # The frontend runs on another origin (Live Server, port 5500), so the
    # browser asks first (preflight) whether the Authorization header is allowed.
    response = client.options(ME_URL, headers = {
        "Origin": "http://localhost:5500",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })

    assert response.status_code == HTTPStatus.OK
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
