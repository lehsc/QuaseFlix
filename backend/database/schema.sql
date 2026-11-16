--
-- PostgreSQL database dump
--

\restrict QvYWveozZ44eJVyyJINScZbazEMMNcaE238XccZoUOKYcnCQdiSMYbCg2TdmJmr

-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: account_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.account_status AS ENUM (
    'TRIAL',
    'ACTIVE',
    'CANCELED'
);


ALTER TYPE public.account_status OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.account (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    cpf character varying(14) NOT NULL,
    birth_date date NOT NULL,
    phone character varying(20),
    address text NOT NULL,
    status public.account_status DEFAULT 'TRIAL'::public.account_status,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    plan_id integer
);


ALTER TABLE public.account OWNER TO postgres;

--
-- Name: account_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.account_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.account_id_seq OWNER TO postgres;

--
-- Name: account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.account_id_seq OWNED BY public.account.id;


--
-- Name: actor; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.actor (
    id integer NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.actor OWNER TO postgres;

--
-- Name: actor_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.actor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.actor_id_seq OWNER TO postgres;

--
-- Name: actor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.actor_id_seq OWNED BY public.actor.id;


--
-- Name: boleto_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.boleto_details (
    payment_method_id integer NOT NULL,
    barcode character varying(255) NOT NULL,
    due_date date NOT NULL
);


ALTER TABLE public.boleto_details OWNER TO postgres;

--
-- Name: credit_card_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.credit_card_details (
    payment_method_id integer NOT NULL,
    card_number character varying(20) NOT NULL,
    holder_name character varying(100) NOT NULL,
    expiration_date date NOT NULL,
    bank_name character varying(50)
);


ALTER TABLE public.credit_card_details OWNER TO postgres;

--
-- Name: director; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.director (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.director OWNER TO postgres;

--
-- Name: director_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.director_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.director_id_seq OWNER TO postgres;

--
-- Name: director_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.director_id_seq OWNED BY public.director.id;


--
-- Name: episode; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.episode (
    id integer NOT NULL,
    season_id integer,
    episode_number integer NOT NULL,
    title character varying(150) NOT NULL,
    duration_minutes integer NOT NULL,
    director_id integer,
    video_url text NOT NULL
);


ALTER TABLE public.episode OWNER TO postgres;

--
-- Name: episode_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.episode_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.episode_id_seq OWNER TO postgres;

--
-- Name: episode_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.episode_id_seq OWNED BY public.episode.id;


--
-- Name: genre; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.genre (
    id integer NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE public.genre OWNER TO postgres;

--
-- Name: genre_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.genre_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.genre_id_seq OWNER TO postgres;

--
-- Name: genre_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.genre_id_seq OWNED BY public.genre.id;


--
-- Name: media; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.media (
    id integer NOT NULL,
    title character varying(150) NOT NULL,
    synopsis text,
    release_year integer
);


ALTER TABLE public.media OWNER TO postgres;

--
-- Name: media_actor; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.media_actor (
    media_id integer NOT NULL,
    actor_id integer NOT NULL
);


ALTER TABLE public.media_actor OWNER TO postgres;

--
-- Name: media_genre; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.media_genre (
    media_id integer NOT NULL,
    genre_id integer NOT NULL
);


ALTER TABLE public.media_genre OWNER TO postgres;

--
-- Name: media_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.media_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.media_id_seq OWNER TO postgres;

--
-- Name: media_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.media_id_seq OWNED BY public.media.id;


--
-- Name: movie; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.movie (
    media_id integer NOT NULL,
    duration_minutes integer NOT NULL,
    director_id integer,
    video_url text NOT NULL
);


ALTER TABLE public.movie OWNER TO postgres;

--
-- Name: payment_method; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payment_method (
    id integer NOT NULL,
    account_id integer,
    type character varying(30) NOT NULL
);


ALTER TABLE public.payment_method OWNER TO postgres;

--
-- Name: payment_method_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payment_method_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payment_method_id_seq OWNER TO postgres;

--
-- Name: payment_method_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payment_method_id_seq OWNED BY public.payment_method.id;


--
-- Name: plan; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.plan (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    price numeric(10,2) NOT NULL,
    description text
);


ALTER TABLE public.plan OWNER TO postgres;

--
-- Name: plan_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.plan_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.plan_id_seq OWNER TO postgres;

--
-- Name: plan_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.plan_id_seq OWNED BY public.plan.id;


--
-- Name: profile; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.profile (
    id integer NOT NULL,
    account_id integer,
    name character varying(100) NOT NULL,
    is_kids boolean DEFAULT false
);


ALTER TABLE public.profile OWNER TO postgres;

--
-- Name: profile_genre; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.profile_genre (
    profile_id integer NOT NULL,
    genre_id integer NOT NULL
);


ALTER TABLE public.profile_genre OWNER TO postgres;

--
-- Name: profile_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.profile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.profile_id_seq OWNER TO postgres;

--
-- Name: profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.profile_id_seq OWNED BY public.profile.id;


--
-- Name: season; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.season (
    id integer NOT NULL,
    series_media_id integer,
    season_number integer NOT NULL,
    title character varying(150)
);


ALTER TABLE public.season OWNER TO postgres;

--
-- Name: season_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.season_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.season_id_seq OWNER TO postgres;

--
-- Name: season_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.season_id_seq OWNED BY public.season.id;


--
-- Name: series; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.series (
    media_id integer NOT NULL
);


ALTER TABLE public.series OWNER TO postgres;

--
-- Name: account id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account ALTER COLUMN id SET DEFAULT nextval('public.account_id_seq'::regclass);


--
-- Name: actor id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.actor ALTER COLUMN id SET DEFAULT nextval('public.actor_id_seq'::regclass);


--
-- Name: director id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.director ALTER COLUMN id SET DEFAULT nextval('public.director_id_seq'::regclass);


--
-- Name: episode id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.episode ALTER COLUMN id SET DEFAULT nextval('public.episode_id_seq'::regclass);


--
-- Name: genre id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.genre ALTER COLUMN id SET DEFAULT nextval('public.genre_id_seq'::regclass);


--
-- Name: media id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media ALTER COLUMN id SET DEFAULT nextval('public.media_id_seq'::regclass);


--
-- Name: payment_method id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payment_method ALTER COLUMN id SET DEFAULT nextval('public.payment_method_id_seq'::regclass);


--
-- Name: plan id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.plan ALTER COLUMN id SET DEFAULT nextval('public.plan_id_seq'::regclass);


--
-- Name: profile id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.profile ALTER COLUMN id SET DEFAULT nextval('public.profile_id_seq'::regclass);


--
-- Name: season id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.season ALTER COLUMN id SET DEFAULT nextval('public.season_id_seq'::regclass);


--
-- Name: account account_cpf_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_cpf_key UNIQUE (cpf);


--
-- Name: account account_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_email_key UNIQUE (email);


--
-- Name: account account_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_pkey PRIMARY KEY (id);


--
-- Name: actor actor_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.actor
    ADD CONSTRAINT actor_pkey PRIMARY KEY (id);


--
-- Name: boleto_details boleto_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.boleto_details
    ADD CONSTRAINT boleto_details_pkey PRIMARY KEY (payment_method_id);


--
-- Name: credit_card_details credit_card_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credit_card_details
    ADD CONSTRAINT credit_card_details_pkey PRIMARY KEY (payment_method_id);


--
-- Name: director director_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.director
    ADD CONSTRAINT director_pkey PRIMARY KEY (id);


--
-- Name: episode episode_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.episode
    ADD CONSTRAINT episode_pkey PRIMARY KEY (id);


--
-- Name: episode episode_season_id_episode_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.episode
    ADD CONSTRAINT episode_season_id_episode_number_key UNIQUE (season_id, episode_number);


--
-- Name: genre genre_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.genre
    ADD CONSTRAINT genre_name_key UNIQUE (name);


--
-- Name: genre genre_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.genre
    ADD CONSTRAINT genre_pkey PRIMARY KEY (id);


--
-- Name: media_actor media_actor_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media_actor
    ADD CONSTRAINT media_actor_pkey PRIMARY KEY (media_id, actor_id);


--
-- Name: media_genre media_genre_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media_genre
    ADD CONSTRAINT media_genre_pkey PRIMARY KEY (media_id, genre_id);


--
-- Name: media media_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media
    ADD CONSTRAINT media_pkey PRIMARY KEY (id);


--
-- Name: movie movie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movie
    ADD CONSTRAINT movie_pkey PRIMARY KEY (media_id);


--
-- Name: payment_method payment_method_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT payment_method_pkey PRIMARY KEY (id);


--
-- Name: plan plan_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.plan
    ADD CONSTRAINT plan_pkey PRIMARY KEY (id);


--
-- Name: profile_genre profile_genre_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.profile_genre
    ADD CONSTRAINT profile_genre_pkey PRIMARY KEY (profile_id, genre_id);


--
-- Name: profile profile_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.profile
    ADD CONSTRAINT profile_pkey PRIMARY KEY (id);


--
-- Name: season season_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.season
    ADD CONSTRAINT season_pkey PRIMARY KEY (id);


--
-- Name: season season_series_media_id_season_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.season
    ADD CONSTRAINT season_series_media_id_season_number_key UNIQUE (series_media_id, season_number);


--
-- Name: series series_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_pkey PRIMARY KEY (media_id);


--
-- Name: account account_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plan(id);


--
-- Name: boleto_details boleto_details_payment_method_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.boleto_details
    ADD CONSTRAINT boleto_details_payment_method_id_fkey FOREIGN KEY (payment_method_id) REFERENCES public.payment_method(id) ON DELETE CASCADE;


--
-- Name: credit_card_details credit_card_details_payment_method_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credit_card_details
    ADD CONSTRAINT credit_card_details_payment_method_id_fkey FOREIGN KEY (payment_method_id) REFERENCES public.payment_method(id) ON DELETE CASCADE;


--
-- Name: episode episode_director_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.episode
    ADD CONSTRAINT episode_director_id_fkey FOREIGN KEY (director_id) REFERENCES public.director(id) ON DELETE SET NULL;


--
-- Name: episode episode_season_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.episode
    ADD CONSTRAINT episode_season_id_fkey FOREIGN KEY (season_id) REFERENCES public.season(id) ON DELETE CASCADE;


--
-- Name: media_actor media_actor_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media_actor
    ADD CONSTRAINT media_actor_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actor(id) ON DELETE CASCADE;


--
-- Name: media_actor media_actor_media_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media_actor
    ADD CONSTRAINT media_actor_media_id_fkey FOREIGN KEY (media_id) REFERENCES public.media(id) ON DELETE CASCADE;


--
-- Name: media_genre media_genre_genre_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media_genre
    ADD CONSTRAINT media_genre_genre_id_fkey FOREIGN KEY (genre_id) REFERENCES public.genre(id) ON DELETE CASCADE;


--
-- Name: media_genre media_genre_media_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media_genre
    ADD CONSTRAINT media_genre_media_id_fkey FOREIGN KEY (media_id) REFERENCES public.media(id) ON DELETE CASCADE;


--
-- Name: movie movie_director_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movie
    ADD CONSTRAINT movie_director_id_fkey FOREIGN KEY (director_id) REFERENCES public.director(id) ON DELETE SET NULL;


--
-- Name: movie movie_media_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movie
    ADD CONSTRAINT movie_media_id_fkey FOREIGN KEY (media_id) REFERENCES public.media(id) ON DELETE CASCADE;


--
-- Name: payment_method payment_method_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT payment_method_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.account(id) ON DELETE CASCADE;


--
-- Name: profile profile_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.profile
    ADD CONSTRAINT profile_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.account(id) ON DELETE CASCADE;


--
-- Name: profile_genre profile_genre_genre_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.profile_genre
    ADD CONSTRAINT profile_genre_genre_id_fkey FOREIGN KEY (genre_id) REFERENCES public.genre(id) ON DELETE CASCADE;


--
-- Name: profile_genre profile_genre_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.profile_genre
    ADD CONSTRAINT profile_genre_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profile(id) ON DELETE CASCADE;


--
-- Name: season season_series_media_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.season
    ADD CONSTRAINT season_series_media_id_fkey FOREIGN KEY (series_media_id) REFERENCES public.series(media_id) ON DELETE CASCADE;


--
-- Name: series series_media_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_media_id_fkey FOREIGN KEY (media_id) REFERENCES public.media(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

-- Catalog metadata and lookup indexes (also migration 002).
ALTER TABLE public.media ADD COLUMN popularity_score integer NOT NULL
    DEFAULT 0 CHECK (popularity_score >= 0);

CREATE TABLE public.media_language (
    media_id integer NOT NULL REFERENCES public.media(id) ON DELETE CASCADE,
    kind varchar(8) NOT NULL CHECK (kind IN ('audio', 'subtitle')),
    language varchar(100) NOT NULL CHECK (length(trim(language)) > 0),
    PRIMARY KEY (media_id, kind, language)
);

CREATE INDEX media_genre_genre_idx ON public.media_genre (genre_id, media_id);
CREATE INDEX media_actor_actor_idx ON public.media_actor (actor_id, media_id);
CREATE INDEX movie_director_idx ON public.movie (director_id);
CREATE INDEX episode_director_idx ON public.episode (director_id);
CREATE INDEX media_title_idx ON public.media (lower(title), id);
CREATE INDEX media_popularity_idx ON public.media (popularity_score DESC, lower(title), id);

\unrestrict QvYWveozZ44eJVyyJINScZbazEMMNcaE238XccZoUOKYcnCQdiSMYbCg2TdmJmr


ALTER TABLE public.account ADD COLUMN IF NOT EXISTS full_name text;
CREATE TABLE IF NOT EXISTS public.registration_session (
 token_hash text PRIMARY KEY, email text NOT NULL, code_hash text NOT NULL,
 expires_at timestamp NOT NULL, attempts integer NOT NULL DEFAULT 0,
 verified boolean NOT NULL DEFAULT false, google_subject text
);
CREATE UNIQUE INDEX IF NOT EXISTS account_email_normalized ON public.account (lower(email));
ALTER TABLE public.account ADD COLUMN IF NOT EXISTS google_subject text UNIQUE;

ALTER TABLE public.account ADD COLUMN IF NOT EXISTS next_billing_at timestamp;
ALTER TABLE public.account ADD COLUMN IF NOT EXISTS canceled_at timestamp;
UPDATE public.account SET next_billing_at=created_at + interval '30 days'
WHERE next_billing_at IS NULL AND status <> 'CANCELED';
CREATE TABLE IF NOT EXISTS public.subscription_invoice (
 id bigserial PRIMARY KEY,
 account_id integer NOT NULL REFERENCES public.account(id) ON DELETE CASCADE,
 period_start timestamp NOT NULL,
 amount numeric(10,2) NOT NULL CHECK (amount >= 0),
 due_at timestamp NOT NULL,
 paid_at timestamp,
 payment_method_id integer REFERENCES public.payment_method(id) ON DELETE SET NULL,
 barcode text,
 UNIQUE(account_id, period_start)
);
CREATE TABLE IF NOT EXISTS public.billing_outbox (
 id bigserial PRIMARY KEY,
 invoice_id bigint NOT NULL UNIQUE REFERENCES public.subscription_invoice(id) ON DELETE CASCADE,
 recipient text NOT NULL,
 body text NOT NULL,
 delivered_at timestamp
);

BEGIN;
-- Fail visibly if legacy data needs manual reconciliation; never delete profiles.
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM public.profile WHERE account_id IS NULL OR btrim(name)='') THEN
        RAISE EXCEPTION 'Profile migration: resolve orphaned profiles and empty names first';
    END IF;
    IF EXISTS (SELECT 1 FROM public.profile GROUP BY account_id HAVING count(*)>4) THEN
        RAISE EXCEPTION 'Profile migration: accounts with more than four profiles need review';
    END IF;
    IF EXISTS (SELECT 1 FROM public.profile GROUP BY account_id,lower(btrim(name)) HAVING count(*)>1) THEN
        RAISE EXCEPTION 'Profile migration: resolve duplicate names within each account first';
    END IF;
END $$;
UPDATE public.profile SET name=btrim(name), is_kids=COALESCE(is_kids,false);
ALTER TABLE public.profile ALTER COLUMN account_id SET NOT NULL;
ALTER TABLE public.profile ALTER COLUMN is_kids SET NOT NULL;
ALTER TABLE public.profile DROP CONSTRAINT IF EXISTS profile_name_nonempty;
ALTER TABLE public.profile ADD CONSTRAINT profile_name_nonempty CHECK (name=btrim(name) AND length(name)>0);
CREATE UNIQUE INDEX IF NOT EXISTS profile_account_name_unique ON public.profile(account_id,lower(name));

INSERT INTO public.profile(account_id,name,is_kids)
SELECT a.id,'Principal',false FROM public.account a
WHERE NOT EXISTS (SELECT 1 FROM public.profile p WHERE p.account_id=a.id);

CREATE OR REPLACE FUNCTION public.create_default_profile() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO public.profile(account_id,name,is_kids) VALUES (NEW.id,'Principal',false);
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS account_default_profile ON public.account;
CREATE TRIGGER account_default_profile AFTER INSERT ON public.account
FOR EACH ROW EXECUTE FUNCTION public.create_default_profile();

CREATE TABLE IF NOT EXISTS public.profile_session (
    token_hash text PRIMARY KEY,
    account_id integer NOT NULL REFERENCES public.account(id) ON DELETE CASCADE,
    profile_id integer REFERENCES public.profile(id) ON DELETE SET NULL,
    parental_locked boolean NOT NULL DEFAULT false,
    created_at timestamp NOT NULL DEFAULT LOCALTIMESTAMP
);
CREATE INDEX IF NOT EXISTS profile_session_account ON public.profile_session(account_id);

INSERT INTO public.genre(name) VALUES
('Ação'),('Animação'),('Aventura'),('Comédia'),('Documentário'),('Drama'),('Fantasia'),('Ficção científica')
ON CONFLICT(name) DO NOTHING;

-- NULL means unclassified and is excluded from child-profile content.
ALTER TABLE public.media ADD COLUMN IF NOT EXISTS age_rating smallint;
ALTER TABLE public.media DROP CONSTRAINT IF EXISTS media_age_rating_valid;
ALTER TABLE public.media ADD CONSTRAINT media_age_rating_valid CHECK (age_rating IN (0,10,12,14,16,18));
COMMIT;

-- Module 5: per-profile playback resume point and selected tracks (migration 005).
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
