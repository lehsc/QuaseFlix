-- Safe to reapply; existing catalog rows are preserved.
BEGIN;

ALTER TABLE public.media ADD COLUMN IF NOT EXISTS popularity_score integer NOT NULL
    DEFAULT 0 CHECK (popularity_score >= 0);

CREATE TABLE IF NOT EXISTS public.media_language (
    media_id integer NOT NULL REFERENCES public.media(id) ON DELETE CASCADE,
    kind varchar(8) NOT NULL CHECK (kind IN ('audio', 'subtitle')),
    language varchar(100) NOT NULL CHECK (length(trim(language)) > 0),
    PRIMARY KEY (media_id, kind, language)
);

CREATE INDEX IF NOT EXISTS media_genre_genre_idx ON public.media_genre (genre_id, media_id);
CREATE INDEX IF NOT EXISTS media_actor_actor_idx ON public.media_actor (actor_id, media_id);
CREATE INDEX IF NOT EXISTS movie_director_idx ON public.movie (director_id);
CREATE INDEX IF NOT EXISTS episode_director_idx ON public.episode (director_id);
CREATE INDEX IF NOT EXISTS media_title_idx ON public.media (lower(title), id);
CREATE INDEX IF NOT EXISTS media_popularity_idx ON public.media (popularity_score DESC, lower(title), id);

COMMIT;
