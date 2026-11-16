"""Subscription lifecycle. All payments are simulated; no external provider is called."""
import calendar
import secrets
from datetime import timedelta

from fastapi import HTTPException
from psycopg.rows import dict_row

from backend.database.connection import get_db_connection


def next_month(value):
    month = value.month % 12 + 1
    year = value.year + (value.month == 12)
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def lock_account(cur, account_id):
    cur.execute("SELECT *, LOCALTIMESTAMP AS now FROM public.account WHERE id=%s FOR UPDATE", (account_id,))
    account = cur.fetchone()
    if not account:
        raise HTTPException(404, "Account not found.")
    return account


def payment_method(cur, account_id, method_id=None):
    cur.execute("""SELECT pm.id, pm.type, cc.expiration_date
        FROM public.payment_method pm LEFT JOIN public.credit_card_details cc
        ON cc.payment_method_id=pm.id WHERE pm.account_id=%s
        AND (%s::integer IS NULL OR pm.id=%s) ORDER BY pm.id DESC LIMIT 1""",
        (account_id, method_id, method_id))
    return cur.fetchone()


def card_succeeds(method, now):
    return bool(method and method['type'] == 'credit_card' and
                method['expiration_date'] and method['expiration_date'] >= now.date())


def issue_invoice(cur, account, period):
    cur.execute("SELECT price FROM public.plan WHERE id=%s", (account['plan_id'],))
    plan = cur.fetchone()
    if not plan:
        raise HTTPException(409, "Choose a valid plan before billing.")
    method = payment_method(cur, account['id'])
    boleto = bool(method and method['type'] == 'boleto')
    barcode = ''.join(secrets.choice('0123456789') for _ in range(47)) if boleto else None
    paid = account['now'] if plan['price'] == 0 or card_succeeds(method, account['now']) else None
    due = period + timedelta(days=3) if boleto else period
    cur.execute("""INSERT INTO public.subscription_invoice
        (account_id,period_start,amount,due_at,paid_at,payment_method_id,barcode)
        VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(account_id,period_start) DO NOTHING RETURNING id""",
        (account['id'], period, plan['price'], due, paid, method['id'] if method else None, barcode))
    invoice = cur.fetchone()
    if invoice:
        body = f"Simulated subscription invoice: {plan['price']}. Due: {due.isoformat()}. "
        body += f"Boleto: {barcode}." if boleto else ('Payment confirmed.' if paid else 'Payment failed; update your payment method.')
        cur.execute("INSERT INTO public.billing_outbox(invoice_id,recipient,body) VALUES (%s,%s,%s)",
                    (invoice['id'], account['email'], body))


def accrue(cur, account):
    if account['status'] == 'CANCELED':
        return
    due = account['next_billing_at'] or account['created_at'] + timedelta(days=30)
    # Account row lock and invoice uniqueness make worker retries safe.
    while due <= account['now']:
        issue_invoice(cur, account, due)
        due = next_month(due)
        account['status'] = 'ACTIVE'
    account['next_billing_at'] = due
    cur.execute("UPDATE public.account SET next_billing_at=%s,status=%s WHERE id=%s",
                (due, account['status'], account['id']))


def manage(account_id, action='view', method_id=None):
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            account = lock_account(cur, account_id)
            accrue(cur, account)
            if action == 'pay':
                method = payment_method(cur, account_id, method_id)
                if not method or (method['type'] == 'credit_card' and not card_succeeds(method, account['now'])):
                    raise HTTPException(422, "Select an owned, valid payment method.")
                # Explicit user confirmation simulates boleto settlement too.
                cur.execute("UPDATE public.subscription_invoice SET paid_at=%s,payment_method_id=%s WHERE account_id=%s AND paid_at IS NULL",
                            (account['now'], method['id'], account_id))
            if action in ('cancel', 'restore'):
                cur.execute("SELECT 1 FROM public.subscription_invoice WHERE account_id=%s AND paid_at IS NULL LIMIT 1", (account_id,))
                if cur.fetchone():
                    raise HTTPException(409, "Settle outstanding invoices first.")
                if action == 'cancel':
                    cur.execute("UPDATE public.account SET status='CANCELED',canceled_at=LOCALTIMESTAMP,next_billing_at=NULL WHERE id=%s", (account_id,))
                    account['status'], account['next_billing_at'] = 'CANCELED', None
                elif account['status'] == 'CANCELED':
                    trial_end = account['created_at'] + timedelta(days=30)
                    account['status'] = 'TRIAL' if account['now'] < trial_end else 'ACTIVE'
                    cur.execute('SELECT MAX(period_start) AS last_period FROM public.subscription_invoice WHERE account_id=%s AND paid_at IS NOT NULL', (account_id,))
                    last_period = cur.fetchone()['last_period']
                    covered_until = next_month(last_period) if last_period else account['now']
                    account['next_billing_at'] = trial_end if account['status'] == 'TRIAL' else max(account['now'], covered_until)
                    cur.execute("UPDATE public.account SET status=%s,canceled_at=NULL,next_billing_at=%s WHERE id=%s",
                                (account['status'], account['next_billing_at'], account_id))
                    accrue(cur, account)
            cur.execute("SELECT * FROM public.subscription_invoice WHERE account_id=%s ORDER BY period_start DESC", (account_id,))
            invoices = cur.fetchall()
            cur.execute("SELECT id,type FROM public.payment_method WHERE account_id=%s ORDER BY id DESC", (account_id,))
            methods = cur.fetchall()
            return dict(status=account['status'].lower(), trial_ends_at=account['created_at'] + timedelta(days=30),
                        next_billing_at=account['next_billing_at'], invoices=invoices, payment_methods=methods,
                        outstanding=sum(i['amount'] for i in invoices if i['paid_at'] is None), mode='simulated')


def ensure_paid(account_id):
    from backend.exceptions import SubscriptionExpiredError
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM public.subscription_invoice WHERE account_id=%s AND paid_at IS NULL AND due_at<=LOCALTIMESTAMP LIMIT 1", (account_id,))
            if cur.fetchone():
                raise SubscriptionExpiredError(account_id, "There are overdue subscription invoices. Settle them in subscription management.")


def run_billing():
    """Called by the worker. Each account commits independently."""
    import logging
    with get_db_connection() as conn:
        ids = conn.execute("SELECT id FROM public.account WHERE status <> 'CANCELED' AND COALESCE(next_billing_at,created_at + interval '30 days')<=LOCALTIMESTAMP").fetchall()
    for (account_id,) in ids:
        try:
            manage(account_id)
        except Exception:
            logging.getLogger(__name__).exception('Billing failed for account %s', account_id)
