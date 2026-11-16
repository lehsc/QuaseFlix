"""Catalog's search and navegation against real PostgreSQL, rolled back after each test.

Use a test DATABASE_URL with schema.sql applied. Only catalog access is stubbed;
the router, service, SQL and response serialization run together.
"""
from contextlib import contextmanager
from datetime import datetime
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from backend.database.connection import DATABASE_URL
from backend.main import app
from backend.models.account_status import AccountStatus
from backend.models.authenticated_account import AuthenticatedAccount
from backend.routers.auth import get_current_account
from backend.services import catalog_services


@pytest.fixture
def catalog(monkeypatch):
    conn = psycopg.connect(DATABASE_URL)
    try:
        with conn.cursor() as cursor:
            def insert(sql, params=()):
                cursor.execute(sql + " RETURNING id", params)
                return cursor.fetchone()[0]

            genre = insert("INSERT INTO public.genre (name) VALUES (%s)", (f"Test-{uuid.uuid4().hex}",))
            other_genre = insert("INSERT INTO public.genre (name) VALUES (%s)", (f"Other-{uuid.uuid4().hex}",))
            empty_genre = insert("INSERT INTO public.genre (name) VALUES (%s)", (f"Empty-{uuid.uuid4().hex}",))
            director = insert("INSERT INTO public.director (name) VALUES (%s)", ("Helena Duarte",))
            episode_director = insert("INSERT INTO public.director (name) VALUES (%s)", ("Rui Prado",))
            actor = insert("INSERT INTO public.actor (name) VALUES (%s)", ("Alice Mendes",))
            second_actor = insert("INSERT INTO public.actor (name) VALUES (%s)", ("Alice Costa",))

            def media(title, kind, score=0):
                media_id = insert("INSERT INTO public.media (title, synopsis, release_year, popularity_score) VALUES (%s, %s, %s, %s)",
                                  (title, "Uma jornada inesquecível.", 2026, score))
                cursor.execute("INSERT INTO public.media_genre VALUES (%s, %s)", (media_id, genre))
                if kind == "movie":
                    cursor.execute("INSERT INTO public.movie VALUES (%s, 110, %s, 'private://movie')", (media_id, director))
                elif kind == "series":
                    cursor.execute("INSERT INTO public.series VALUES (%s)", (media_id,))
                return media_id

            movie = media("A Viagem", "movie", 10)
            series = media("B Horizontes", "series", 80)
            literal = media("C 100%_Real!", "movie", 30)
            sparse = media("D Sem metadados", "series")
            orphan = media("Z Ainda indisponível", None, 1000)
            cursor.execute("UPDATE public.media SET synopsis = NULL, release_year = NULL WHERE id = %s", (sparse,))
            cursor.execute("UPDATE public.movie SET director_id = NULL WHERE media_id = %s", (literal,))
            cursor.execute("INSERT INTO public.media_genre VALUES (%s, %s)", (movie, other_genre))
            for media_id in [movie, series]:
                for actor_id in [actor, second_actor]:
                    cursor.execute("INSERT INTO public.media_actor VALUES (%s, %s)", (media_id, actor_id))
                for kind, language in [("audio", "Português"), ("audio", "Inglês"), ("subtitle", "Português")]:
                    cursor.execute("INSERT INTO public.media_language VALUES (%s, %s, %s)", (media_id, kind, language))

            # Deliberately insert seasons/episodes out of order.
            season2 = insert("INSERT INTO public.season (series_media_id, season_number, title) VALUES (%s, 2, 'Recomeços')", (series,))
            season1 = insert("INSERT INTO public.season (series_media_id, season_number, title) VALUES (%s, 1, 'Origens')", (series,))
            insert("INSERT INTO public.season (series_media_id, season_number) VALUES (%s, 3)", (series,))
            for season, number, minutes, director_id in [(season2, 1, 50, director), (season1, 2, 45, episode_director), (season1, 1, 40, episode_director)]:
                insert("INSERT INTO public.episode (season_id, episode_number, title, duration_minutes, director_id, video_url) VALUES (%s, %s, %s, %s, %s, 'private://episode')",
                       (season, number, f"Episódio {number}", minutes, director_id))

        @contextmanager
        def transaction_connection():
            yield conn
        monkeypatch.setattr(catalog_services, "get_db_connection", transaction_connection)
        previous_override = app.dependency_overrides.get(get_current_account)
        app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
            7, "catalog@example.com", AccountStatus.ACTIVE, 1, datetime.now())
        try:
            with TestClient(app) as client:
                yield dict(client=client, conn=conn, genre=genre, other_genre=other_genre, empty_genre=empty_genre,
                           movie=movie, series=series, literal=literal, sparse=sparse, orphan=orphan)
        finally:
            if previous_override is None:
                app.dependency_overrides.pop(get_current_account, None)
            else:
                app.dependency_overrides[get_current_account] = previous_override
    finally:
        conn.rollback()
        conn.close()


def browse(catalog, **params):
    response = catalog["client"].get("/api/catalog", params={"genre_id": catalog["genre"], **params})
    assert response.status_code == 200, response.text
    return response.json()


def ids(data):
    return [item["id"] for item in data["items"]]


def test_rf10_catalog_formats_genres_and_no_duplicates(catalog):
    data = browse(catalog)
    assert ids(data) == [catalog[k] for k in ["movie", "series", "literal", "sparse"]]
    assert data["total"] == 4
    assert data["suggestions"] == []
    assert [item["media_type"] for item in data["items"]] == ["movie", "series", "movie", "series"]
    assert len(data["items"][0]["genres"]) == 2
    assert ids(browse(catalog, media_type="movie")) == [catalog["movie"], catalog["literal"]]
    assert ids(browse(catalog, media_type="series")) == [catalog["series"], catalog["sparse"]]


def test_rf10_combined_genre_and_format(catalog):
    assert ids(browse(catalog, genre_id=catalog["other_genre"], media_type="movie")) == [catalog["movie"]]
    assert browse(catalog, genre_id=catalog["other_genre"], media_type="series")["total"] == 0


def test_rf10_lists_genres(catalog):
    response = catalog["client"].get("/api/catalog/genres")
    assert response.status_code == 200
    assert {catalog["genre"], catalog["other_genre"]} <= {g["id"] for g in response.json()}


def test_rf10_pagination(catalog):
    first = browse(catalog, limit=2)
    second = browse(catalog, limit=2, offset=2)
    assert first["total"] == second["total"] == 4
    assert ids(first) + ids(second) == ids(browse(catalog))
    assert first["limit"] == 2 and second["offset"] == 2
    beyond = browse(catalog, q="Viagem", offset=24)
    assert beyond["total"] == 1 and beyond["items"] == beyond["suggestions"] == []


def test_rf11_complete_movie_metadata(catalog):
    response = catalog["client"].get(f"/api/catalog/{catalog['movie']}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "A Viagem" and data["release_year"] == 2026
    assert data["synopsis"] == "Uma jornada inesquecível."
    assert data["duration_minutes"] == 110
    assert len(data["genres"]) == 2
    assert data["actors"] == ["Alice Costa", "Alice Mendes"]
    assert data["directors"] == ["Helena Duarte"]
    assert set(data["audio_languages"]) == {"Português", "Inglês"}
    assert data["subtitle_languages"] == ["Português"]
    assert data["season_count"] == data["episode_count"] == 0
    assert data["seasons"] == []
    assert "video_url" not in response.text and "private://" not in response.text


def test_rf11_series_seasons_episodes_and_directors(catalog):
    response = catalog["client"].get(f"/api/catalog/{catalog['series']}")
    assert response.status_code == 200
    data = response.json()
    assert data["season_count"] == 3 and data["episode_count"] == 3
    assert data["duration_minutes"] == 135
    assert data["directors"] == ["Helena Duarte", "Rui Prado"]
    assert [s["season_number"] for s in data["seasons"]] == [1, 2, 3]
    episodes = data["seasons"][0]["episodes"]
    assert [e["episode_number"] for e in episodes] == [1, 2]
    assert [e["duration_minutes"] for e in episodes] == [40, 45]
    assert episodes[0]["director"] == "Rui Prado"
    assert data["seasons"][2]["episodes"] == []
    assert "video_url" not in response.text and "private://" not in response.text


def test_rf11_missing_optional_metadata_and_empty_series(catalog):
    response = catalog["client"].get(f"/api/catalog/{catalog['sparse']}")
    assert response.status_code == 200
    data = response.json()
    assert data["synopsis"] is None and data["release_year"] is None
    assert data["duration_minutes"] == data["season_count"] == data["episode_count"] == 0
    for key in ["actors", "directors", "audio_languages", "subtitle_languages", "seasons"]:
        assert data[key] == []


def test_rf11_untyped_or_deleted_media_not_found(catalog):
    assert catalog["client"].get(f"/api/catalog/{catalog['orphan']}").status_code == 404
    with catalog["conn"].cursor() as cursor:
        cursor.execute("DELETE FROM public.media WHERE id = %s", (catalog["movie"],))
    assert catalog["client"].get(f"/api/catalog/{catalog['movie']}").status_code == 404


@pytest.mark.parametrize("query,expected", [
    ("viaGEM", ["movie"]), ("  Horizontes  ", ["series"]),
    ("Alice", ["movie", "series"]), ("mEnDeS", ["movie", "series"]),
    ("Helena", ["movie", "series"]), ("rUi pRa", ["series"]),
    ("%", ["literal"]), ("_", ["literal"]), ("!", ["literal"]),
    ("%_Real!", ["literal"]), ("   ", ["movie", "series", "literal", "sparse"]),
])
def test_rf12_search_title_actor_movie_and_episode_director(catalog, query, expected):
    data = browse(catalog, q=query)
    assert ids(data) == [catalog[k] for k in expected]
    assert data["total"] == len(expected)
    assert data["suggestions"] == []


def test_rf12_search_combines_filters(catalog):
    assert ids(browse(catalog, q="Alice", media_type="series")) == [catalog["series"]]
    assert ids(browse(catalog, q="Alice", genre_id=catalog["other_genre"])) == [catalog["movie"]]


@pytest.mark.parametrize("query", ["no-such-title", "' OR 1=1 --", "\\"])
def test_scenario7_no_results_suggests_popular_productions(catalog, query):
    data = browse(catalog, q=query)
    assert data["items"] == [] and data["total"] == 0
    assert [m["id"] for m in data["suggestions"]] == [catalog[k] for k in ["series", "literal", "movie", "sparse"]]


def test_suggestions_preserve_filters_and_empty_catalog(catalog):
    data = browse(catalog, q="not-found", media_type="movie", genre_id=catalog["other_genre"])
    assert [m["id"] for m in data["suggestions"]] == [catalog["movie"]]
    empty = browse(catalog, q="not-found", genre_id=catalog["empty_genre"])
    assert empty["items"] == empty["suggestions"] == [] and empty["total"] == 0


def test_rf11_language_constraints_and_cascade(catalog):
    # Savepoints let the fixture continue after each deliberately invalid insert.
    for kind, language in [("dub", "Português"), ("audio", "   "), ("audio", "Português")]:
        with pytest.raises(psycopg.IntegrityError), catalog["conn"].transaction():
            catalog["conn"].execute("INSERT INTO public.media_language VALUES (%s, %s, %s)", (catalog["movie"], kind, language))
    catalog["conn"].execute("DELETE FROM public.media WHERE id = %s", (catalog["movie"],))
    assert catalog["conn"].execute("SELECT count(*) FROM public.media_language WHERE media_id = %s", (catalog["movie"],)).fetchone()[0] == 0
