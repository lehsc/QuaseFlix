"""
Integration tests for the plan endpoints (real PostgreSQL database, see the
README). The account_id fixture lives in conftest.py. Plan 1 must exist, as
registering an account assigns it by default.
"""
import uuid
from decimal import Decimal
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import get_db_connection
from backend.main import app
from backend.routers import plans

client = TestClient(app)

NON_EXISTENT_ID = 2_147_483_647  # largest value of an integer column


@pytest.fixture
def extra_plan():
    """A plan created just for the test (and removed afterwards)."""
    name = f"Plano teste {uuid.uuid4().hex[:8]}"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Explicit id: plan 1 is inserted with an explicit id (README), so
            # the sequence may still point to 1 and a default id would collide.
            cursor.execute(
                """
                INSERT INTO public.plan (id, name, price, description)
                SELECT COALESCE(MAX(id), 0) + 1, %s, %s, %s FROM public.plan
                RETURNING id
                """,
                (name, Decimal("19.90"), "Plano criado pelos testes.")
            )
            plan_id = cursor.fetchone()[0]

    yield {
        "id": plan_id,
        "name": name,
        "price": 19.9,
        "description": "Plano criado pelos testes.",
    }

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Accounts that chose this plan are test accounts: a plan cannot be
            # deleted while an account references it.
            cursor.execute("DELETE FROM public.account WHERE plan_id = %s", (plan_id,))
            cursor.execute("DELETE FROM public.plan WHERE id = %s", (plan_id,))


def get_account_plan_id(account_id: int) -> int:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT plan_id FROM public.account WHERE id = %s", (account_id,))
            return cursor.fetchone()[0]


def test_list_plans(extra_plan):
    response = client.get("/api/plans")

    assert response.status_code == HTTPStatus.OK
    plans_list = response.json()
    assert extra_plan in plans_list
    # Cheapest first
    prices = [plan["price"] for plan in plans_list]
    assert prices == sorted(prices)


def test_list_plans_failure(monkeypatch):
    def broken_service():
        raise RuntimeError("database is down")

    monkeypatch.setattr(plans, "service_list_plans", broken_service)

    response = client.get("/api/plans")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Unable to list plans."}


def test_select_plan_success(account_id, extra_plan):
    response = client.put(
        f"/api/accounts/{account_id}/plan", json = {"plan_id": extra_plan["id"]}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "message": "Plan selected successfully!",
        "plan": extra_plan,
    }
    assert get_account_plan_id(account_id) == extra_plan["id"]


def test_select_plan_can_be_changed_again(account_id, extra_plan):
    first = client.put(f"/api/accounts/{account_id}/plan", json = {"plan_id": extra_plan["id"]})
    second = client.put(f"/api/accounts/{account_id}/plan", json = {"plan_id": 1})

    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.OK
    assert get_account_plan_id(account_id) == 1


def test_select_unknown_plan(account_id):
    plan_before = get_account_plan_id(account_id)

    response = client.put(
        f"/api/accounts/{account_id}/plan", json = {"plan_id": NON_EXISTENT_ID}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": f"Plan {NON_EXISTENT_ID} not found."}
    assert get_account_plan_id(account_id) == plan_before


def test_select_plan_for_unknown_account(extra_plan):
    response = client.put(
        f"/api/accounts/{NON_EXISTENT_ID}/plan", json = {"plan_id": extra_plan["id"]}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": f"Account {NON_EXISTENT_ID} not found."}


@pytest.mark.parametrize("payload", [{}, {"plan_id": "abc"}, {"plan_id": 0}, {"plan_id": -1}])
def test_select_plan_with_invalid_body(payload):
    response = client.put("/api/accounts/1/plan", json = payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_select_plan_failure(monkeypatch):
    def broken_service(account_id, plan_id):
        raise RuntimeError("database is down")

    monkeypatch.setattr(plans, "service_select_plan", broken_service)

    response = client.put("/api/accounts/1/plan", json = {"plan_id": 1})

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Unable to select plan."}


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
