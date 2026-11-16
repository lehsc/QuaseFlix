"""Run against an initialized disposable DB using QUASEFLIX_TEST_DATABASE_URL."""
import os
import uuid
from datetime import timedelta
from decimal import Decimal
import pytest
from fastapi import HTTPException
from backend.database import connection
from backend.services.subscription_services import manage, run_billing, ensure_paid
from backend.services.auth_services import authenticate
from backend.exceptions import SubscriptionExpiredError, AccountCanceledError
from backend.security import hash_password

pytestmark = pytest.mark.skipif(not os.environ.get('QUASEFLIX_TEST_DATABASE_URL'), reason='Disposable PostgreSQL test URL not supplied')

@pytest.fixture
def account(monkeypatch):
    monkeypatch.setattr(connection, 'DATABASE_URL', os.environ['QUASEFLIX_TEST_DATABASE_URL'])
    email = f'{uuid.uuid4().hex}@example.com'
    with connection.get_db_connection() as conn:
        plan = conn.execute("INSERT INTO public.plan(name,price) VALUES ('Subscription test',25.90) RETURNING id").fetchone()[0]
        account_id = conn.execute("""INSERT INTO public.account(email,password_hash,cpf,birth_date,address,plan_id,created_at)
        VALUES (%s,%s,%s,'2000-01-01','Test address',%s,LOCALTIMESTAMP - interval '31 days') RETURNING id""",
        (email,hash_password('StrongPass123'),uuid.uuid4().hex[:14],plan)).fetchone()[0]
        method = conn.execute("INSERT INTO public.payment_method(account_id,type) VALUES (%s,'boleto') RETURNING id", (account_id,)).fetchone()[0]
    yield account_id, method, email
    with connection.get_db_connection() as conn:
        conn.execute('DELETE FROM public.account WHERE id=%s',(account_id,))
        conn.execute('DELETE FROM public.plan WHERE id=%s',(plan,))


def test_trial_transition_boleto_retry_and_cancellation(account):
    account_id, method, email = account
    result = manage(account_id)
    assert result['status'] == 'active'
    assert len(result['invoices']) == 1
    invoice = result['invoices'][0]
    assert invoice['amount'] == Decimal('25.90')
    assert len(invoice['barcode']) == 47
    assert invoice['paid_at'] is None
    assert manage(account_id)['invoices'][0]['id'] == invoice['id']
    assert authenticate(email,'StrongPass123').status.value == 'active'
    with pytest.raises(HTTPException) as error:
        manage(account_id,'cancel')
    assert error.value.status_code == 409
    manage(account_id,'pay',method)
    assert manage(account_id,'cancel')['status'] == 'canceled'
    run_billing()
    assert len(manage(account_id)['invoices']) == 1
    with pytest.raises(AccountCanceledError):
        authenticate(email,'StrongPass123')
    assert authenticate(email,'StrongPass123',require_access=False).id == account_id
    restored = manage(account_id,'restore')
    assert restored['status'] == 'active'
    assert len(restored['invoices']) == 1  # already paid for this period


def test_trial_cancellation_and_restoration_does_not_restart_trial(account):
    account_id, _, _ = account
    with connection.get_db_connection() as conn:
        conn.execute("UPDATE public.account SET created_at=LOCALTIMESTAMP - interval '5 days' WHERE id=%s",(account_id,))
    first = manage(account_id,'cancel')
    assert not first['invoices']
    restored = manage(account_id,'restore')
    assert restored['status'] == 'trial'
    assert restored['trial_ends_at'] == first['trial_ends_at']
    assert not restored['invoices']


def test_overdue_payment_and_foreign_method(account):
    account_id, method, _ = account
    manage(account_id)
    with connection.get_db_connection() as conn:
        conn.execute("UPDATE public.subscription_invoice SET due_at=LOCALTIMESTAMP - interval '1 second' WHERE account_id=%s",(account_id,))
    with pytest.raises(SubscriptionExpiredError):
        ensure_paid(account_id)
    with pytest.raises(HTTPException):
        manage(account_id,'pay',2147483647)
    assert manage(account_id)['outstanding'] == Decimal('25.90')
    manage(account_id,'pay',method)
    ensure_paid(account_id)


def test_card_billing_recurs_once_per_month(account):
    account_id, method, _ = account
    with connection.get_db_connection() as conn:
        conn.execute("UPDATE public.payment_method SET type='credit_card' WHERE id=%s",(method,))
        conn.execute("INSERT INTO public.credit_card_details(payment_method_id,card_number,holder_name,expiration_date) VALUES (%s,'************1111','Test Person',CURRENT_DATE + interval '1 year')",(method,))
    first = manage(account_id)
    assert first['outstanding'] == 0
    assert first['invoices'][0]['paid_at']
    with connection.get_db_connection() as conn:
        conn.execute("UPDATE public.account SET next_billing_at=LOCALTIMESTAMP - interval '1 hour' WHERE id=%s",(account_id,))
    run_billing()
    run_billing()
    result = manage(account_id)
    assert len(result['invoices']) == 2
    assert result['outstanding'] == 0
    with connection.get_db_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM public.billing_outbox WHERE invoice_id IN (SELECT id FROM public.subscription_invoice WHERE account_id=%s)',(account_id,)).fetchone()[0] == 2


def test_concurrent_billing_creates_one_invoice(account):
    from concurrent.futures import ThreadPoolExecutor
    account_id, _, _ = account
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(manage, [account_id, account_id]))
    assert len(results[0]['invoices']) == len(results[1]['invoices']) == 1
    assert results[0]['invoices'][0]['id'] == results[1]['invoices'][0]['id']


def test_restore_after_trial_does_not_bill_canceled_months(account):
    account_id, _, _ = account
    with connection.get_db_connection() as conn:
        conn.execute("UPDATE public.account SET status='CANCELED',created_at=LOCALTIMESTAMP - interval '100 days' WHERE id=%s",(account_id,))
    result = manage(account_id,'restore')
    assert result['status'] == 'active'
    assert len(result['invoices']) == 1
    assert result['outstanding'] == Decimal('25.90')


def test_expired_card_records_unpaid_invoice_and_blocks_access(account):
    account_id, method, _ = account
    with connection.get_db_connection() as conn:
        conn.execute("UPDATE public.payment_method SET type='credit_card' WHERE id=%s",(method,))
        conn.execute("INSERT INTO public.credit_card_details(payment_method_id,card_number,holder_name,expiration_date) VALUES (%s,'************1111','Test Person',CURRENT_DATE - interval '1 month')",(method,))
    result = manage(account_id)
    assert result['outstanding'] == Decimal('25.90')
    with pytest.raises(SubscriptionExpiredError):
        ensure_paid(account_id)
    with pytest.raises(HTTPException):
        manage(account_id,'pay',method)


def test_billing_outbox_delivery_is_repeatable(account,monkeypatch,tmp_path):
    from backend.billing_worker import deliver_outbox
    manage(account[0])
    monkeypatch.setenv('QUASEFLIX_OUTBOX',str(tmp_path))
    deliver_outbox()
    names = sorted(p.name for p in tmp_path.iterdir())
    assert len(names) == 1
    deliver_outbox()
    assert sorted(p.name for p in tmp_path.iterdir()) == names
