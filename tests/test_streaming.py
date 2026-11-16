"""Focused unit tests for Module 5 source and playback-state rules."""
from contextlib import contextmanager

import pytest

from backend.exceptions import EpisodeRequiredError, MediaNotFoundError, PlaybackOptionError
from backend.services import streaming_services


class FakeCursor:
    def __init__(self, target, languages=(), progress=None):
        self.target = target
        self.languages = list(languages)
        self.progress = progress
        self.current = None
        self.write = None

    def __enter__(self): return self
    def __exit__(self, *_): pass

    def execute(self, sql, params=()):
        if "FROM public.media m" in sql:
            self.current = "target"
        elif "FROM public.media_language" in sql:
            self.current = "languages"
        elif "FROM public.playback_progress" in sql:
            self.current = "progress"
        elif "INSERT INTO public.playback_progress" in sql:
            self.current = "write"
            self.write = (sql, params)
        return self

    def fetchone(self):
        return {**self.target} if self.current == "target" and self.target else (
            {**self.progress} if self.current == "progress" and self.progress else None)

    def fetchall(self):
        return [{**row} for row in self.languages] if self.current == "languages" else []


class FakeConnection:
    def __init__(self, cursor): self._cursor = cursor
    def cursor(self, **_): return self._cursor


def fake_db(monkeypatch, cursor):
    @contextmanager
    def connection():
        yield FakeConnection(cursor)
    monkeypatch.setattr(streaming_services, "get_db_connection", connection)


def movie_target(url="https://cdn.example/movie/master.m3u8"):
    return dict(
        media_id=10, title="Uma obra", age_rating=12, is_movie=True,
        movie_duration=10, movie_url=url, episode_id=None, episode_title=None,
        episode_duration=None, episode_url=None,
    )


def series_target(found=True):
    return dict(
        media_id=20, title="Uma série", age_rating=12, is_movie=False,
        movie_duration=None, movie_url=None, episode_id=30 if found else None,
        episode_title="Piloto" if found else None, episode_duration=42 if found else None,
        episode_url="https://cdn.example/series/30.mpd" if found else None,
    )


def test_rf13_hls_session_resumes_per_profile_and_rf14_lists_tracks(monkeypatch):
    cursor = FakeCursor(
        movie_target(),
        languages=[{"kind": "audio", "language": "Inglês"},
                   {"kind": "audio", "language": "Português"},
                   {"kind": "subtitle", "language": "Português"}],
        progress={"position_seconds": 78.25, "completed": False,
                  "audio_language": "Inglês", "subtitle_language": "Português"},
    )
    fake_db(monkeypatch, cursor)
    result = streaming_services.get_playback(3, 10)
    assert result.content_type == "movie"
    assert result.stream_type == "application/vnd.apple.mpegurl" and result.adaptive
    assert result.duration_seconds == 600 and result.resume_position_seconds == 78.25
    assert [track.language for track in result.audio_tracks] == ["Inglês", "Português"]
    assert result.selected_audio == "Inglês" and result.selected_subtitle == "Português"


def test_completed_content_restarts_from_zero(monkeypatch):
    cursor = FakeCursor(movie_target(), progress={
        "position_seconds": 599, "completed": True,
        "audio_language": None, "subtitle_language": None,
    })
    fake_db(monkeypatch, cursor)
    result = streaming_services.get_playback(3, 10)
    assert result.completed is True
    assert result.resume_position_seconds == 0


def test_child_profile_cannot_bypass_catalog_with_direct_stream_url(monkeypatch):
    cursor = FakeCursor(movie_target())
    fake_db(monkeypatch, cursor)
    with pytest.raises(MediaNotFoundError):
        streaming_services.get_playback(3, 10, restricted=True)


def test_series_requires_its_own_existing_episode(monkeypatch):
    cursor = FakeCursor(series_target(found=False))
    fake_db(monkeypatch, cursor)
    with pytest.raises(EpisodeRequiredError):
        streaming_services.get_playback(3, 20)
    with pytest.raises(MediaNotFoundError):
        streaming_services.get_playback(3, 20, 999)


def test_unknown_or_untyped_media_is_not_playable(monkeypatch):
    cursor = FakeCursor(None)
    fake_db(monkeypatch, cursor)
    with pytest.raises(MediaNotFoundError):
        streaming_services.get_playback(3, 999)


def test_dash_episode_is_adaptive(monkeypatch):
    cursor = FakeCursor(series_target())
    fake_db(monkeypatch, cursor)
    result = streaming_services.get_playback(3, 20, 30)
    assert result.content_type == "episode" and result.episode_id == 30
    assert result.stream_type == "application/dash+xml" and result.adaptive


def test_rf13_saves_exact_point_and_marks_last_five_seconds_complete(monkeypatch):
    cursor = FakeCursor(movie_target(), languages=[
        {"kind": "audio", "language": "Português"},
        {"kind": "subtitle", "language": "Inglês"},
    ])
    fake_db(monkeypatch, cursor)
    result = streaming_services.save_progress(3, 10, None, 596.125, "Português", "Inglês")
    assert result.position_seconds == 596.125 and result.completed is True
    assert cursor.write is not None
    assert "WHERE episode_id IS NULL" in cursor.write[0]
    assert cursor.write[1][3] == 596.125


@pytest.mark.parametrize("audio,subtitle", [("Klingon", None), (None, "Élfico")])
def test_rf14_only_accepts_available_tracks(monkeypatch, audio, subtitle):
    cursor = FakeCursor(movie_target(), languages=[
        {"kind": "audio", "language": "Português"},
        {"kind": "subtitle", "language": "Inglês"},
    ])
    fake_db(monkeypatch, cursor)
    with pytest.raises(PlaybackOptionError):
        streaming_services.save_progress(3, 10, None, 10, audio, subtitle)


def test_progress_cannot_exceed_server_duration(monkeypatch):
    cursor = FakeCursor(movie_target())
    fake_db(monkeypatch, cursor)
    with pytest.raises(PlaybackOptionError):
        streaming_services.save_progress(3, 10, None, 601, None, None)


@pytest.mark.parametrize("url,mime,adaptive", [
    ("https://cdn/x.M3U8?token=secret", "application/vnd.apple.mpegurl", True),
    ("https://cdn/x.mpd", "application/dash+xml", True),
    ("https://cdn/x.mp4", "video/mp4", False),
])
def test_stream_type_detection_ignores_query_string(url, mime, adaptive):
    assert streaming_services._stream_type(url) == (mime, adaptive)
