from psycopg.rows import dict_row

from backend.database.connection import get_db_connection
from backend.exceptions import MediaNotFoundError
from backend.schemas.catalog_schema import (
    CatalogSchema, GenreSchema, MediaDetailSchema, MediaSummarySchema, MediaType,
)

_FROM = """
    FROM public.media m
    LEFT JOIN public.movie movie ON movie.media_id = m.id
    LEFT JOIN public.series series ON series.media_id = m.id
"""
_SUMMARY = """
    m.id, m.title, m.release_year, m.age_rating,
    CASE WHEN movie.media_id IS NOT NULL THEN 'movie' ELSE 'series' END AS media_type,
    ARRAY(SELECT g.name FROM public.genre g
          JOIN public.media_genre mg ON mg.genre_id = g.id
          WHERE mg.media_id = m.id ORDER BY g.name, g.id) AS genres
"""


def _filters(media_type=None, genre_id=None, query=None, restricted=False):
    # Untyped media are not available works in the catalog.
    clauses = ["(movie.media_id IS NOT NULL OR series.media_id IS NOT NULL)"]
    params = []
    if restricted:
        clauses.append("m.age_rating = 0")
    if media_type == "movie":
        clauses.append("movie.media_id IS NOT NULL")
    elif media_type == "series":
        clauses.append("series.media_id IS NOT NULL")
    if genre_id is not None:
        clauses.append("""EXISTS (SELECT 1 FROM public.media_genre mg
                                 WHERE mg.media_id = m.id AND mg.genre_id = %s)""")
        params.append(genre_id)
    if query:
        # Treat LIKE metacharacters as literal search text, not wildcards.
        term = query.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        pattern = f"%{term}%"
        clauses.append("""(
            m.title ILIKE %s ESCAPE '!'
            OR EXISTS (SELECT 1 FROM public.media_actor ma
                       JOIN public.actor a ON a.id = ma.actor_id
                       WHERE ma.media_id = m.id AND a.name ILIKE %s ESCAPE '!')
            OR EXISTS (SELECT 1 FROM public.director d
                       WHERE d.id = movie.director_id AND d.name ILIKE %s ESCAPE '!')
            OR EXISTS (SELECT 1 FROM public.season s
                       JOIN public.episode e ON e.season_id = s.id
                       JOIN public.director d ON d.id = e.director_id
                       WHERE s.series_media_id = series.media_id
                       AND d.name ILIKE %s ESCAPE '!')
        )""")
        params.extend([pattern] * 4)
    return " WHERE " + " AND ".join(clauses), params


def list_genres() -> list[GenreSchema]:
    with get_db_connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SELECT id, name FROM public.genre ORDER BY name, id")
        return [GenreSchema(**row) for row in cursor.fetchall()]


def list_catalog(
    query: str = "", media_type: MediaType | None = None,
    genre_id: int | None = None, limit: int = 24, offset: int = 0,
    restricted: bool = False,
    preferred_genre_ids: tuple[int, ...] = (),
) -> CatalogSchema:
    query = query.strip()
    where, params = _filters(media_type, genre_id, query, restricted)
    preference_order = ""
    order_params = []
    if preferred_genre_ids:
        preference_order = """(SELECT count(*) FROM public.media_genre preferred
            WHERE preferred.media_id=m.id AND preferred.genre_id=ANY(%s)) DESC, """
        order_params = [list(preferred_genre_ids)]
    with get_db_connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SELECT COUNT(*) AS total " + _FROM + where, params)
        total = cursor.fetchone()["total"]
        cursor.execute(
            "SELECT " + _SUMMARY + _FROM + where
            + " ORDER BY " + preference_order + "LOWER(m.title), m.id LIMIT %s OFFSET %s",
            [*params, *order_params, limit, offset],
        )
        items = [MediaSummarySchema(**row) for row in cursor.fetchall()]
        suggestions = []
        if query and total == 0:
            # Keep the selected format/genre when suggesting popular works.
            fallback_where, fallback_params = _filters(media_type, genre_id, restricted=restricted)
            cursor.execute(
                "SELECT " + _SUMMARY + _FROM + fallback_where
                + " ORDER BY " + preference_order + "m.popularity_score DESC, LOWER(m.title), m.id LIMIT 6",
                [*fallback_params, *order_params],
            )
            suggestions = [MediaSummarySchema(**row) for row in cursor.fetchall()]
    return CatalogSchema(items=items, total=total, limit=limit, offset=offset,
                         suggestions=suggestions)


def get_media(media_id: int) -> MediaDetailSchema:
    with get_db_connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT " + _SUMMARY + ", m.synopsis, movie.duration_minutes "
            + _FROM + " WHERE m.id = %s AND (movie.media_id IS NOT NULL OR series.media_id IS NOT NULL)",
            (media_id,),
        )
        media = cursor.fetchone()
        if media is None:
            raise MediaNotFoundError(media_id)

        cursor.execute("""
            SELECT a.name FROM public.actor a
            JOIN public.media_actor ma ON ma.actor_id = a.id
            WHERE ma.media_id = %s ORDER BY a.name, a.id
        """, (media_id,))
        media["actors"] = [row["name"] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT d.id, d.name FROM public.director d
            WHERE d.id IN (
                SELECT director_id FROM public.movie WHERE media_id = %s
                UNION
                SELECT e.director_id FROM public.episode e
                JOIN public.season s ON s.id = e.season_id WHERE s.series_media_id = %s
            ) ORDER BY d.name, d.id
        """, (media_id, media_id))
        media["directors"] = [row["name"] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT kind, language FROM public.media_language
            WHERE media_id = %s ORDER BY language
        """, (media_id,))
        languages = cursor.fetchall()
        media["audio_languages"] = [r["language"] for r in languages if r["kind"] == "audio"]
        media["subtitle_languages"] = [r["language"] for r in languages if r["kind"] == "subtitle"]

        seasons = []
        if media["media_type"] == "series":
            cursor.execute("""
                SELECT id, season_number, title FROM public.season
                WHERE series_media_id = %s ORDER BY season_number, id
            """, (media_id,))
            seasons = cursor.fetchall()
            cursor.execute("""
                SELECT e.id, e.season_id, e.episode_number, e.title, e.duration_minutes,
                       d.name AS director
                FROM public.episode e JOIN public.season s ON s.id = e.season_id
                LEFT JOIN public.director d ON d.id = e.director_id
                WHERE s.series_media_id = %s ORDER BY s.season_number, e.episode_number, e.id
            """, (media_id,))
            episodes = cursor.fetchall()
            by_season = {s["id"]: [] for s in seasons}
            for episode in episodes:
                by_season[episode.pop("season_id")].append(episode)
            for season in seasons:
                season["episodes"] = by_season[season["id"]]
            media["duration_minutes"] = sum(e["duration_minutes"] for e in episodes)

        media["seasons"] = seasons
        media["season_count"] = len(seasons)
        media["episode_count"] = sum(len(s["episodes"]) for s in seasons)
        return MediaDetailSchema(**media)
