"""Module 5 HTTP authorization, validation and error mapping (no database)."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend.exceptions import (
    AccountCanceledError,
    EpisodeRequiredError,
    MediaNotFoundError,
    PlaybackOptionError,
    SubscriptionExpiredError,
)
from backend.main import app
from backend.models.account_status import AccountStatus
from backend.models.authenticated_account import AuthenticatedAccount
from backend.routers import auth
from backend.schemas.streaming_schema import PlaybackProgressSchema, PlaybackSessionSchema
from backend.security import create_access_token
from backend.services import profile_services, streaming_services


def playback(**changes):
    values = dict(
        media_id=10, episode_id=None, title="Filme de teste", episode_title=None,
        content_type="movie", stream_url="https://cdn.example/movie/master.m3u8",
        stream_type="application/vnd.apple.mpegurl", adaptive=True,
        duration_seconds=600, resume_position_seconds=42.5, completed=False,
        audio_tracks=[{"language": "Português"}, {"language": "Inglês"}],
        subtitle_tracks=[{"language": "Português"}], selected_audio="Português",
        selected_subtitle=None,
    )
    values.update(changes)
    return PlaybackSessionSchema(**values)


@pytest.fixture
def streaming_client(monkeypatch):
    account = AuthenticatedAccount(7, "viewer@example.com", AccountStatus.ACTIVE, 1, datetime.now())
    monkeypatch.setattr(auth, "service_get_account_for_access", lambda account_id: account)
    monkeypatch.setattr(profile_services, "current_selection", lambda *args: {
        "profile": dict(id=3, account_id=7, name="Principal", is_kids=False,
                        restricted=False, genre_ids=()), "restricted": False})
    monkeypatch.setattr(streaming_services, "get_playback", lambda *args, **kwargs: playback())
    monkeypatch.setattr(streaming_services, "save_progress", lambda *args, **kwargs: PlaybackProgressSchema(
        position_seconds=args[3], completed=False, audio_language=args[4], subtitle_language=args[5]))
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {create_access_token(7)}"
        yield client


@pytest.mark.parametrize("path,method", [
    ("/api/streaming/10", "get"),
    ("/api/streaming/10/progress", "put"),
])
@pytest.mark.parametrize("token", [None, "bad-token", create_access_token(7, now=0)])
def test_rf13_requires_authentication(path, method, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with TestClient(app) as client:
        response = client.get(path, headers=headers) if method == "get" else client.put(
            path, headers=headers, json={"position_seconds": 10})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_rf13_returns_adaptive_source_tracks_and_resume_point(streaming_client):
    response = streaming_client.get("/api/streaming/10")
    assert response.status_code == 200
    data = response.json()
    assert data["stream_url"].endswith("master.m3u8")
    assert data["adaptive"] is True
    assert data["resume_position_seconds"] == 42.5
    assert [track["language"] for track in data["audio_tracks"]] == ["Português", "Inglês"]
    assert [track["language"] for track in data["subtitle_tracks"]] == ["Português"]


@pytest.mark.parametrize("error,status", [
    (AccountCanceledError(7), 403),
    (SubscriptionExpiredError(7), 402),
])
@pytest.mark.parametrize("path,method", [
    ("/api/streaming/10", "get"),
    ("/api/streaming/10/progress", "put"),
])
def test_rf13_rejects_canceled_or_expired_accounts(
    streaming_client, monkeypatch, error, status, path, method,
):
    def denied(account_id):
        raise error
    monkeypatch.setattr(auth, "service_get_account_for_access", denied)
    response = streaming_client.get(path) if method == "get" else streaming_client.put(
        path, json={"position_seconds": 10})
    assert response.status_code == status


def test_rf13_series_requires_an_episode(streaming_client, monkeypatch):
    def required(*args, **kwargs):
        raise EpisodeRequiredError(10)
    monkeypatch.setattr(streaming_services, "get_playback", required)
    response = streaming_client.get("/api/streaming/10")
    assert response.status_code == 409
    assert "Select an episode" in response.json()["detail"]


def test_rf13_episode_is_forwarded_and_missing_target_is_404(streaming_client, monkeypatch):
    seen = []
    monkeypatch.setattr(streaming_services, "get_playback", lambda *args, **kwargs: seen.append(args) or playback(
        episode_id=22, episode_title="Piloto", content_type="episode"))
    assert streaming_client.get("/api/streaming/10?episode_id=22").status_code == 200
    assert seen[0] == (3, 10, 22)

    def missing(*args, **kwargs):
        raise MediaNotFoundError(10)
    monkeypatch.setattr(streaming_services, "get_playback", missing)
    assert streaming_client.get("/api/streaming/10?episode_id=999").status_code == 404


def test_rf13_requires_selected_profile(streaming_client, monkeypatch):
    monkeypatch.setattr(profile_services, "current_selection", lambda *args: {
        "profile": None, "restricted": True})
    assert streaming_client.get("/api/streaming/10").status_code == 409


def test_rf13_parental_policy_is_enforced_for_direct_playback_urls(streaming_client, monkeypatch):
    restrictions = []
    monkeypatch.setattr(profile_services, "current_selection", lambda *args: {
        "profile": dict(id=4, account_id=7, name="Infantil", is_kids=True,
                        restricted=True, genre_ids=()), "restricted": True})
    def protected(*args, **kwargs):
        restrictions.append(kwargs["restricted"])
        raise MediaNotFoundError(10)
    monkeypatch.setattr(streaming_services, "get_playback", protected)
    assert streaming_client.get("/api/streaming/10").status_code == 404
    assert restrictions == [True]


def test_rf13_progress_and_rf14_choices_are_forwarded(streaming_client, monkeypatch):
    seen = []
    monkeypatch.setattr(streaming_services, "save_progress", lambda *args, **kwargs: seen.append((args, kwargs)) or PlaybackProgressSchema(
        position_seconds=args[3], completed=False, audio_language=args[4], subtitle_language=args[5]))
    response = streaming_client.put("/api/streaming/10/progress", json={
        "position_seconds": 125.75,
        "audio_language": "Inglês",
        "subtitle_language": "Português",
    })
    assert response.status_code == 200
    assert seen[0][0] == (3, 10, None, 125.75, "Inglês", "Português")
    assert seen[0][1] == {"restricted": False}


@pytest.mark.parametrize("payload", [
    {}, {"position_seconds": -1}, {"position_seconds": "later"},
    {"position_seconds": 1, "audio_language": "x" * 101},
])
def test_progress_payload_validation(streaming_client, payload):
    assert streaming_client.put("/api/streaming/10/progress", json=payload).status_code == 422


def test_rf14_rejects_an_unavailable_track(streaming_client, monkeypatch):
    def rejected(*args, **kwargs):
        raise PlaybackOptionError("Klingon")
    monkeypatch.setattr(streaming_services, "save_progress", rejected)
    response = streaming_client.put("/api/streaming/10/progress", json={
        "position_seconds": 5, "audio_language": "Klingon"})
    assert response.status_code == 422
    assert "Klingon" in response.json()["detail"]


@pytest.mark.parametrize("path,method,service,message", [
    ("/api/streaming/10", "get", "get_playback", "Unable to prepare playback."),
    ("/api/streaming/10/progress", "put", "save_progress", "Unable to save playback progress."),
])
def test_streaming_database_failure_is_not_exposed(
    streaming_client, monkeypatch, path, method, service, message,
):
    def broken(*args, **kwargs):
        raise RuntimeError("private database information")
    monkeypatch.setattr(streaming_services, service, broken)
    response = streaming_client.get(path) if method == "get" else streaming_client.put(
        path, json={"position_seconds": 10})
    assert response.status_code == 500
    assert response.json() == {"detail": message}


@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_streaming_ids_are_positive_integers(streaming_client, value):
    assert streaming_client.get(f"/api/streaming/{value}").status_code == 422
    assert streaming_client.get(f"/api/streaming/10?episode_id={value}").status_code == 422
