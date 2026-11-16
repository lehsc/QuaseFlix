from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from backend.main import app
from backend.services import subscription_services as service
from backend.routers import subscriptions
from backend.exceptions import SubscriptionExpiredError


def test_month_rollover():
    assert service.next_month(datetime(2026, 1, 31, 12)) == datetime(2026, 2, 28, 12)
    assert service.next_month(datetime(2024, 1, 31)) == datetime(2024, 2, 29)
    assert service.next_month(datetime(2026, 12, 1)) == datetime(2027, 1, 1)


def test_expired_card_does_not_succeed():
    assert not service.card_succeeds({'type':'credit_card','expiration_date':datetime(2025,1,1).date()}, datetime(2026,1,1))


def test_canceled_account_never_accrues():
    cursor = MagicMock()
    service.accrue(cursor, {'status':'CANCELED'})
    cursor.execute.assert_not_called()


def test_management_requires_authentication():
    client = TestClient(app)
    for path in ('/cancel', '/restore', '/pay'):
        response = client.post('/api/subscription' + path, json={'payment_method_id':1})
        assert response.status_code == 401


def test_management_login_does_not_require_active_subscription(monkeypatch):
    def authenticate(email, password, require_access):
        assert not require_access
        return SimpleNamespace(id=7)
    monkeypatch.setattr(subscriptions, 'authenticate', authenticate)
    response = TestClient(app).post('/api/subscription/login', json={'email':'user@example.com','password':'password'})
    assert response.status_code == 200
    assert response.json()['token']


def test_overdue_invoice_blocks_access(monkeypatch):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
    @contextmanager
    def connection():
        yield conn
    monkeypatch.setattr(service, 'get_db_connection', connection)
    with pytest.raises(SubscriptionExpiredError):
        service.ensure_paid(7)
