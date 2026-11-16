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
