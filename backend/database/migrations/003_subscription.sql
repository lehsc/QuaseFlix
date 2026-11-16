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
