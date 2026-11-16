"""Playback authorization, source discovery and per-profile resume state."""
from urllib.parse import urlsplit

from psycopg.rows import dict_row

from backend.database.connection import get_db_connection
from backend.exceptions import EpisodeRequiredError, MediaNotFoundError, PlaybackOptionError
from backend.schemas.streaming_schema import (
    PlaybackProgressSchema,
    PlaybackSessionSchema,
    PlaybackTrackSchema,
)


def _stream_type(url: str) -> tuple[str, bool]:
    path = urlsplit(url).path.lower()
    if path.endswith(".m3u8"):
        return "application/vnd.apple.mpegurl", True
    if path.endswith(".mpd"):
        return "application/dash+xml", True
    return "video/mp4", False


def _load_target(cursor, media_id: int, episode_id: int | None) -> dict:
    cursor.execute("""
        SELECT m.id AS media_id, m.title, m.age_rating,
               movie.media_id IS NOT NULL AS is_movie,
               movie.duration_minutes AS movie_duration,
               movie.video_url AS movie_url,
               e.id AS episode_id, e.title AS episode_title,
               e.duration_minutes AS episode_duration, e.video_url AS episode_url
        FROM public.media m
        LEFT JOIN public.movie movie ON movie.media_id = m.id
        LEFT JOIN public.series series ON series.media_id = m.id
        LEFT JOIN (
            SELECT episode.id, episode.title, episode.duration_minutes,
                   episode.video_url, season.series_media_id
            FROM public.episode episode
            JOIN public.season season ON season.id = episode.season_id
        ) e ON e.series_media_id = series.media_id AND e.id = %s
        WHERE m.id = %s AND (movie.media_id IS NOT NULL OR series.media_id IS NOT NULL)
        LIMIT 1
    """, (episode_id, media_id))
    target = cursor.fetchone()
    if target is None:
        raise MediaNotFoundError(media_id)
    if target["is_movie"]:
        if episode_id is not None:
            raise MediaNotFoundError(media_id)
        target.update(content_type="movie", duration_minutes=target["movie_duration"],
                      stream_url=target["movie_url"], episode_id=None, episode_title=None)
    else:
        if episode_id is None:
            raise EpisodeRequiredError(media_id)
        if target["episode_id"] is None:
            # Do not reveal whether an episode belongs to some other title.
            raise MediaNotFoundError(media_id)
        target.update(content_type="episode", duration_minutes=target["episode_duration"],
                      stream_url=target["episode_url"])
    return target


def _load_languages(cursor, media_id: int) -> tuple[list[str], list[str]]:
    cursor.execute("""
        SELECT kind, language FROM public.media_language
        WHERE media_id = %s ORDER BY kind, language
    """, (media_id,))
    rows = cursor.fetchall()
    return (
        [row["language"] for row in rows if row["kind"] == "audio"],
        [row["language"] for row in rows if row["kind"] == "subtitle"],
    )


def _load_progress(cursor, profile_id: int, media_id: int, episode_id: int | None) -> dict | None:
    cursor.execute("""
        SELECT position_seconds, completed, audio_language, subtitle_language
        FROM public.playback_progress
        WHERE profile_id = %s AND media_id = %s
          AND episode_id IS NOT DISTINCT FROM %s
    """, (profile_id, media_id, episode_id))
    return cursor.fetchone()


def _require_allowed_target(target: dict, restricted: bool) -> None:
    if restricted and target["age_rating"] != 0:
        # Match catalog behavior and do not disclose restricted title metadata.
        raise MediaNotFoundError(target["media_id"])


def get_playback(
    profile_id: int, media_id: int, episode_id: int | None = None,
    restricted: bool = False,
) -> PlaybackSessionSchema:
    with get_db_connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
        target = _load_target(cursor, media_id, episode_id)
        _require_allowed_target(target, restricted)
        audio, subtitles = _load_languages(cursor, media_id)
        progress = _load_progress(cursor, profile_id, media_id, target["episode_id"])

    duration_seconds = target["duration_minutes"] * 60
    completed = bool(progress and progress["completed"])
    resume = 0.0 if completed else float(progress["position_seconds"] if progress else 0)
    stream_type, adaptive = _stream_type(target["stream_url"])
    return PlaybackSessionSchema(
        media_id=media_id,
        episode_id=target["episode_id"],
        title=target["title"],
        episode_title=target["episode_title"],
        content_type=target["content_type"],
        stream_url=target["stream_url"],
        stream_type=stream_type,
        adaptive=adaptive,
        duration_seconds=duration_seconds,
        resume_position_seconds=resume,
        completed=completed,
        audio_tracks=[PlaybackTrackSchema(language=value) for value in audio],
        subtitle_tracks=[PlaybackTrackSchema(language=value) for value in subtitles],
        selected_audio=progress["audio_language"] if progress else None,
        selected_subtitle=progress["subtitle_language"] if progress else None,
    )


def save_progress(
    profile_id: int,
    media_id: int,
    episode_id: int | None,
    position_seconds: float,
    audio_language: str | None,
    subtitle_language: str | None,
    restricted: bool = False,
) -> PlaybackProgressSchema:
    with get_db_connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
        target = _load_target(cursor, media_id, episode_id)
        _require_allowed_target(target, restricted)
        audio, subtitles = _load_languages(cursor, media_id)
        if audio_language is not None and audio_language not in audio:
            raise PlaybackOptionError(audio_language)
        if subtitle_language is not None and subtitle_language not in subtitles:
            raise PlaybackOptionError(subtitle_language)

        duration_seconds = target["duration_minutes"] * 60
        if position_seconds > duration_seconds:
            raise PlaybackOptionError("position exceeds content duration")
        completed = position_seconds >= max(0, duration_seconds - 5)
        values = (profile_id, media_id, target["episode_id"], position_seconds,
                  completed, audio_language, subtitle_language)
        if target["episode_id"] is None:
            conflict = "(profile_id, media_id) WHERE episode_id IS NULL"
        else:
            conflict = "(profile_id, episode_id) WHERE episode_id IS NOT NULL"
        cursor.execute(f"""
            INSERT INTO public.playback_progress
                (profile_id, media_id, episode_id, position_seconds, completed,
                 audio_language, subtitle_language)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT {conflict} DO UPDATE SET
                position_seconds = EXCLUDED.position_seconds,
                completed = EXCLUDED.completed,
                audio_language = EXCLUDED.audio_language,
                subtitle_language = EXCLUDED.subtitle_language,
                updated_at = CURRENT_TIMESTAMP
        """, values)
    return PlaybackProgressSchema(
        position_seconds=position_seconds,
        completed=completed,
        audio_language=audio_language,
        subtitle_language=subtitle_language,
    )
