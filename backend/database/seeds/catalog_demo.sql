-- Optional fictional data for exploring Module 4. Run after schema/migration 002.
-- Re-running this script does not duplicate its sample catalog.
-- The file is UTF-8, regardless of the Windows terminal's default encoding.
SET client_encoding = 'UTF8';
BEGIN;
DO $$
DECLARE
    drama_id integer;
    adventure_id integer;
    comedy_id integer;
    director_id integer;
    actor_id integer;
    movie_id integer;
    comedy_movie_id integer;
    series_id integer;
    season_id integer;
BEGIN
    IF EXISTS (SELECT 1 FROM public.media WHERE title = 'Horizontes de Minas (Demo)') THEN
        RETURN;
    END IF;
    INSERT INTO public.genre (name) VALUES ('Drama'), ('Aventura'), ('Comédia')
        ON CONFLICT (name) DO NOTHING;
    SELECT id INTO drama_id FROM public.genre WHERE name = 'Drama';
    SELECT id INTO adventure_id FROM public.genre WHERE name = 'Aventura';
    SELECT id INTO comedy_id FROM public.genre WHERE name = 'Comédia';
    INSERT INTO public.director (name) VALUES ('Clara Andrade') RETURNING id INTO director_id;
    INSERT INTO public.actor (name) VALUES ('Lucas Almeida') RETURNING id INTO actor_id;

    INSERT INTO public.media (title, synopsis, release_year, popularity_score)
        VALUES ('Horizontes de Minas (Demo)', 'Dois amigos percorrem o interior de Minas Gerais em busca de histórias de suas famílias.', 2026, 90)
        RETURNING id INTO movie_id;
    INSERT INTO public.movie VALUES (movie_id, 105, director_id, 'demo://horizontes');
    INSERT INTO public.media_genre VALUES (movie_id, drama_id), (movie_id, adventure_id);

    INSERT INTO public.media (title, synopsis, release_year, popularity_score)
        VALUES ('O Auto da Compadecida (Demo)', 'Dois amigos trapaceiros enganam os poderosos no sertão nordestino e acabam julgados no céu com a ajuda de Nossa Senhora.', 2000, 70)
        RETURNING id INTO comedy_movie_id;
    INSERT INTO public.movie VALUES (comedy_movie_id, 92, director_id, 'demo://compadecida');
    INSERT INTO public.media_genre VALUES (comedy_movie_id, comedy_id);

    INSERT INTO public.media (title, synopsis, release_year, popularity_score)
        VALUES ('Caminhos do Amanhã (Demo)', 'Uma jovem pesquisadora descobre histórias que conectam gerações de sua cidade.', 2026, 100)
        RETURNING id INTO series_id;
    INSERT INTO public.series VALUES (series_id);
    INSERT INTO public.media_genre VALUES (series_id, drama_id), (series_id, adventure_id);
    INSERT INTO public.season (series_media_id, season_number, title)
        VALUES (series_id, 1, 'Primeiros passos') RETURNING id INTO season_id;
    INSERT INTO public.episode (season_id, episode_number, title, duration_minutes, director_id, video_url)
        VALUES (season_id, 1, 'A descoberta', 42, director_id, 'demo://caminhos/1/1'),
               (season_id, 2, 'Novas pistas', 45, director_id, 'demo://caminhos/1/2');
    INSERT INTO public.season (series_media_id, season_number, title)
        VALUES (series_id, 2, 'Novas jornadas') RETURNING id INTO season_id;
    INSERT INTO public.episode (season_id, episode_number, title, duration_minutes, director_id, video_url)
        VALUES (season_id, 1, 'O reencontro', 48, director_id, 'demo://caminhos/2/1');

    INSERT INTO public.media_actor VALUES (movie_id, actor_id), (comedy_movie_id, actor_id), (series_id, actor_id);
    INSERT INTO public.media_language (media_id, kind, language)
        SELECT id, kind, language
        FROM unnest(ARRAY[movie_id, comedy_movie_id, series_id]) AS works(id)
        CROSS JOIN (VALUES ('audio', 'Português'), ('audio', 'Inglês'), ('subtitle', 'Português')) AS languages(kind, language);
END $$;
COMMIT;
