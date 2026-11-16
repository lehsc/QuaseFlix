"""Fixtures shared by the integration tests (they use the real database)."""
import random
import uuid
from http import HTTPStatus

import pytest

TEST_PASSWORD = "Senha@12345"


@pytest.fixture
def registered_account():
    """
    Registers a real account through the API and deletes it after the test.
    Gives its id, e-mail and the password that was used (the database only
    keeps a hash of it), so the tests can log in with it.
    ON DELETE CASCADE also removes whatever was created for that account
    (payment methods, profiles, ...).
    """
    # Imported here so the unit tests, which do not use this fixture, do not
    # need FastAPI or the database driver just to be collected.
    from fastapi.testclient import TestClient

    from backend.database.connection import get_db_connection
    from backend.main import app

    client = TestClient(app)
    random_cpf = "".join([str(random.randint(0, 9)) for _ in range(11)])
    email = f"user_{uuid.uuid4().hex[:8]}@quaseflix-test.com"
    response = client.post("/api/accounts/", json = {
        "email": email,
        "password": TEST_PASSWORD,
        "cpf": random_cpf,
        "birth_date": "2000-05-15",
        "phone": "31999998888",
        "address": "Avenida Antonio Carlos, 6627",
    })
    assert response.status_code == HTTPStatus.CREATED
    new_account_id = response.json()["id"]

    yield {"id": new_account_id, "email": email, "password": TEST_PASSWORD}

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM public.account WHERE id = %s", (new_account_id,))


@pytest.fixture
def account_id(registered_account):
    """The id of a real account (see registered_account)."""
    return registered_account["id"]
