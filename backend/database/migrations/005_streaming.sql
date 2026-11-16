BEGIN;

-- One resume point per movie or episode and profile.  Partial unique indexes
-- make NULL mean "the movie itself" without allowing duplicate movie rows.
CREATE TABLE IF NOT EXISTS public.playback_progress (
    id bigserial PRIMARY KEY,
    profile_id integer NOT NULL REFERENCES public.profile(id) ON DELETE CASCADE,
    media_id integer NOT NULL REFERENCES public.media(id) ON DELETE CASCADE,
    episode_id integer REFERENCES public.episode(id) ON DELETE CASCADE,
    position_seconds numeric(12,3) NOT NULL DEFAULT 0 CHECK (position_seconds >= 0),
    completed boolean NOT NULL DEFAULT false,
    audio_language varchar(100),
    subtitle_language varchar(100),
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS playback_progress_movie_unique
    ON public.playback_progress (profile_id, media_id) WHERE episode_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS playback_progress_episode_unique
    ON public.playback_progress (profile_id, episode_id) WHERE episode_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS playback_progress_recent
    ON public.playback_progress (profile_id, updated_at DESC);

COMMIT;
