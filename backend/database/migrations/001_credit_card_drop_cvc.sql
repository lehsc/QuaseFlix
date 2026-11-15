-- For databases created BEFORE this change (schema.sql already includes it).
--
-- The CVC is only used to authorize a purchase and must not be stored after
-- that, so credit_card_details no longer has a cvc column. card_number now
-- holds only the masked number (e.g. ************1111).
--
-- Run:
--   psql -h localhost -p 5432 -U postgres -d quaseflix -f backend/database/migrations/001_credit_card_drop_cvc.sql

ALTER TABLE public.credit_card_details DROP COLUMN IF EXISTS cvc;
