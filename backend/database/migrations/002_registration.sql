ALTER TABLE public.account ADD COLUMN IF NOT EXISTS full_name text;
CREATE TABLE IF NOT EXISTS public.registration_session (
 token_hash text PRIMARY KEY, email text NOT NULL, code_hash text NOT NULL,
 expires_at timestamp NOT NULL, attempts integer NOT NULL DEFAULT 0,
 verified boolean NOT NULL DEFAULT false, google_subject text
);
CREATE UNIQUE INDEX IF NOT EXISTS account_email_normalized ON public.account (lower(email));
ALTER TABLE public.account ADD COLUMN IF NOT EXISTS google_subject text UNIQUE;
