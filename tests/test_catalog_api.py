"""Catalog HTTP validation, authentication and error handling (no database)."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend.exceptions import AccountCanceledError, MediaNotFoundError, SubscriptionExpiredError
from backend.main import app
from backend.models.account_status import AccountStatus
from backend.models.authenticated_account import AuthenticatedAccount
from backend.routers import auth
from backend.security import create_access_token
from backend.services import catalog_services
from backend.services import profile_services


@pytest.fixture
def catalog_client(monkeypatch):
    account = AuthenticatedAccount(7, "catalog@example.com", AccountStatus.ACTIVE, 1, datetime.now())
    monkeypatch.setattr(auth, "service_get_account_for_access", lambda account_id: account)
    monkeypatch.setattr(profile_services, "current_selection", lambda *args: {
        "profile": dict(id=1, account_id=7, name="Principal", is_kids=False,
                        restricted=False, genre_ids=()), "restricted": False})
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {create_access_token(7)}"
        yield client


@pytest.mark.parametrize("path", ["/api/catalog", "/api/catalog/genres", "/api/catalog/1"])
@pytest.mark.parametrize("token", [None, "bad-token", create_access_token(7, now=0)])
def test_catalog_requires_valid_session(path, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with TestClient(app) as client:
        response = client.get(path, headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("error,status", [(AccountCanceledError(7), 403), (SubscriptionExpiredError(7), 402)])
@pytest.mark.parametrize("path", ["/api/catalog", "/api/catalog/genres", "/api/catalog/1"])
def test_catalog_rejects_inactive_accounts(catalog_client, monkeypatch, error, status, path):
    def denied(account_id):
        raise error
    monkeypatch.setattr(auth, "service_get_account_for_access", denied)
    assert catalog_client.get(path).status_code == status


@pytest.mark.parametrize("query", [
    "media_type=episode", "genre_id=0", "genre_id=-1", "genre_id=abc",
    "limit=0", "limit=101", "offset=-1", "offset=abc", "q=" + "x" * 201,
])
def test_invalid_filters(catalog_client, query):
    assert catalog_client.get(f"/api/catalog?{query}").status_code == 422


@pytest.mark.parametrize("media_id", ["0", "-1", "invalid"])
def test_invalid_media_id(catalog_client, media_id):
    assert catalog_client.get(f"/api/catalog/{media_id}").status_code == 422


def test_missing_media(catalog_client, monkeypatch):
    def missing(media_id):
        raise MediaNotFoundError(media_id)
    monkeypatch.setattr(catalog_services, "get_media", missing)
    response = catalog_client.get("/api/catalog/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Media 999 not found."}


@pytest.mark.parametrize("path", ["/api/catalog", "/api/catalog/1"])
def test_catalog_requires_a_selected_profile(catalog_client, monkeypatch, path):
    monkeypatch.setattr(profile_services, "current_selection", lambda *args: {
        "profile": None, "restricted": True})
    response = catalog_client.get(path)
    assert response.status_code == 409


@pytest.mark.parametrize("path,service,message", [
    ("/api/catalog", "list_catalog", "Unable to list catalog."),
    ("/api/catalog/genres", "list_genres", "Unable to list genres."),
    ("/api/catalog/1", "get_media", "Unable to retrieve media details."),
])
def test_database_failure_is_not_exposed(catalog_client, monkeypatch, path, service, message):
    def broken(*args, **kwargs):
        raise RuntimeError("private database information")
    monkeypatch.setattr(catalog_services, service, broken)
    response = catalog_client.get(path)
    assert response.status_code == 500
    assert response.json() == {"detail": message}
