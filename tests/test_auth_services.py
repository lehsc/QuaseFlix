"""
Tests for the login rules in backend/services/auth_services.py.

The database is replaced by a fake connection, so they do not need PostgreSQL
(only the psycopg package, which the service module imports):
    PYTHONPATH=. pytest tests/test_auth_services.py
"""
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest

from backend.exceptions import (
    AccountCanceledError,
    AccountNotFoundError,
    InvalidCredentialsError,
    SubscriptionExpiredError,
)
from backend.models.account_status import AccountStatus
from backend.security import hash_password
from backend.services import auth_services

PASSWORD = "Senha@12345"
PASSWORD_HASH = hash_password(PASSWORD)
CREATED_AT = datetime(2026, 1, 1, 12, 0)


class FakeCursor:
    def __init__(self, row, queries):
        self._row = row
        self._queries = queries

    def execute(self, query, params):
        self._queries.append((query, params))

    def fetchone(self):
        return self._row


class FakeConnection:
    def __init__(self, row, queries):
        self._row = row
        self._queries = queries

    @contextmanager
    def cursor(self):
        yield FakeCursor(self._row, self._queries)


@pytest.fixture
def fake_database(monkeypatch):
    """Call it with the row the database must answer; returns the executed queries."""
    queries = []

    def install(row):
        @contextmanager
        def fake_get_db_connection():
            yield FakeConnection(row, queries)

        monkeypatch.setattr(auth_services, "get_db_connection", fake_get_db_connection)
        return queries

    return install


def login_row(status = "TRIAL", created_at = CREATED_AT, now = None, password_hash = PASSWORD_HASH):
    """(id, email, password_hash, status, plan_id, created_at, now) as selected by authenticate()."""
    now = now or created_at + timedelta(days = 1)
    return (7, "maria@example.com", password_hash, status, 1, created_at, now)


def id_row(status = "TRIAL", created_at = CREATED_AT, now = None):
    """(id, email, status, plan_id, created_at, now) as selected by get_account_for_access()."""
    now = now or created_at + timedelta(days = 1)
    return (7, "maria@example.com", status, 1, created_at, now)


# ------------------------------------------------------------- authenticate

def test_authenticate_returns_the_account(fake_database):
    fake_database(login_row())

    account = auth_services.authenticate("maria@example.com", PASSWORD)

    assert account.id == 7
    assert account.email == "maria@example.com"
    assert account.status == AccountStatus.TRIAL
    assert account.plan_id == 1
    assert "password" not in account.to_dict() and "password_hash" not in account.to_dict()


def test_authenticate_removes_spaces_around_the_email(fake_database):
    queries = fake_database(login_row())

    auth_services.authenticate("  maria@example.com ", PASSWORD)

    assert queries[0][1] == ("maria@example.com",)


def test_authenticate_compares_the_email_ignoring_case():
    # The comparison is done by the database; this guards the query itself.
    assert "LOWER(email) = LOWER(%s)" in auth_services._SELECT_BY_EMAIL


def test_authenticate_with_unknown_email(fake_database, monkeypatch):
    fake_database(None)
    wasted = []
    monkeypatch.setattr(auth_services, "burn_password_check", wasted.append)

    with pytest.raises(InvalidCredentialsError):
        auth_services.authenticate("nobody@example.com", PASSWORD)

    # A password check is still done, so the answer takes as long as for a real e-mail.
    assert wasted == [PASSWORD]


def test_authenticate_with_wrong_password(fake_database, monkeypatch):
    fake_database(login_row())
    wasted = []
    monkeypatch.setattr(auth_services, "burn_password_check", wasted.append)

    with pytest.raises(InvalidCredentialsError):
        auth_services.authenticate("maria@example.com", "wrong-password")

    assert wasted == []


@pytest.mark.parametrize("stored_hash", ["", PASSWORD, None])
def test_authenticate_never_accepts_a_stored_value_that_is_not_a_hash(fake_database, stored_hash):
    # e.g. an account created before the passwords started to be hashed
    fake_database(login_row(password_hash = stored_hash))

    with pytest.raises(InvalidCredentialsError):
        auth_services.authenticate("maria@example.com", PASSWORD)


def test_authenticate_canceled_account(fake_database):
    fake_database(login_row(status = "CANCELED"))

    with pytest.raises(AccountCanceledError):
        auth_services.authenticate("maria@example.com", PASSWORD)


def test_authenticate_does_not_reveal_the_status_when_the_password_is_wrong(fake_database):
    fake_database(login_row(status = "CANCELED"))

    with pytest.raises(InvalidCredentialsError):
        auth_services.authenticate("maria@example.com", "wrong-password")


def test_authenticate_trial_that_has_ended(fake_database):
    fake_database(login_row(now = CREATED_AT + timedelta(days = 31)))

    with pytest.raises(SubscriptionExpiredError):
        auth_services.authenticate("maria@example.com", PASSWORD)


def test_authenticate_active_account_after_the_trial(fake_database):
    fake_database(login_row(status = "ACTIVE", now = CREATED_AT + timedelta(days = 200)))

    account = auth_services.authenticate("maria@example.com", PASSWORD)

    assert account.status == AccountStatus.ACTIVE


def test_authenticate_account_without_status_is_a_trial(fake_database):
    fake_database(login_row(status = None))

    assert auth_services.authenticate("maria@example.com", PASSWORD).status == AccountStatus.TRIAL


# ------------------------------------------------- get_account_for_access

def test_get_account_for_access_returns_the_account(fake_database):
    queries = fake_database(id_row(status = "ACTIVE"))

    account = auth_services.get_account_for_access(7)

    assert queries[0][1] == (7,)
    assert (account.id, account.email, account.status) == (7, "maria@example.com", AccountStatus.ACTIVE)


def test_get_account_for_access_unknown_account(fake_database):
    fake_database(None)

    with pytest.raises(AccountNotFoundError):
        auth_services.get_account_for_access(7)


def test_get_account_for_access_canceled_account(fake_database):
    fake_database(id_row(status = "CANCELED"))

    with pytest.raises(AccountCanceledError):
        auth_services.get_account_for_access(7)


def test_get_account_for_access_trial_that_has_ended(fake_database):
    fake_database(id_row(now = CREATED_AT + timedelta(days = 45)))

    with pytest.raises(SubscriptionExpiredError):
        auth_services.get_account_for_access(7)
