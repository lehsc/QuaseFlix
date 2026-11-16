"""
Unit tests for the AuthenticatedAccount model: who may use the service
(no database or API needed):
    PYTHONPATH=. pytest tests/test_authenticated_account_models.py
"""
import dataclasses
from datetime import datetime, timedelta

import pytest

from backend.exceptions import AccountCanceledError, SubscriptionExpiredError
from backend.models.account_status import AccountStatus
from backend.models.authenticated_account import TRIAL_DAYS, AuthenticatedAccount

CREATED_AT = datetime(2026, 1, 1, 12, 0)


def make_account(**overrides) -> AuthenticatedAccount:
    data = dict(
        id = 1,
        email = "maria@example.com",
        status = AccountStatus.TRIAL,
        plan_id = 1,
        created_at = CREATED_AT,
    )
    data.update(overrides)
    return AuthenticatedAccount(**data)


def test_trial_lasts_thirty_days():
    assert TRIAL_DAYS == 30
    assert make_account().trial_ends_at == CREATED_AT + timedelta(days = 30)


def test_trial_end_is_unknown_without_creation_date():
    assert make_account(created_at = None).trial_ends_at is None


def test_to_dict_has_only_non_sensitive_data():
    data = make_account(status = AccountStatus.ACTIVE, plan_id = 2).to_dict()

    assert data == {"id": 1, "email": "maria@example.com", "status": "active", "plan_id": 2}


def test_account_cannot_be_changed():
    account = make_account()

    with pytest.raises(dataclasses.FrozenInstanceError):
        account.status = AccountStatus.ACTIVE


# ----------------------------------------------------------- ensure_can_access

def test_trial_account_can_access_during_the_trial():
    now = CREATED_AT + timedelta(days = 29, hours = 23, minutes = 59)

    make_account().ensure_can_access(now)  # does not raise


def test_trial_account_cannot_access_when_the_trial_ends():
    now = CREATED_AT + timedelta(days = TRIAL_DAYS)

    with pytest.raises(SubscriptionExpiredError) as error:
        make_account(id = 9).ensure_can_access(now)

    assert error.value.account_id == 9


def test_trial_account_cannot_access_after_the_trial():
    now = CREATED_AT + timedelta(days = 90)

    with pytest.raises(SubscriptionExpiredError, match = "trial"):
        make_account().ensure_can_access(now)


def test_trial_account_without_creation_date_can_access():
    make_account(created_at = None).ensure_can_access(CREATED_AT + timedelta(days = 365))


def test_active_account_can_access_after_the_trial():
    now = CREATED_AT + timedelta(days = 365)

    make_account(status = AccountStatus.ACTIVE).ensure_can_access(now)


def test_canceled_account_cannot_access():
    with pytest.raises(AccountCanceledError, match = "canceled") as error:
        make_account(id = 4, status = AccountStatus.CANCELED).ensure_can_access(CREATED_AT)

    assert error.value.account_id == 4


def test_canceled_account_cannot_access_even_inside_the_trial_period():
    now = CREATED_AT + timedelta(days = 1)

    with pytest.raises(AccountCanceledError):
        make_account(status = AccountStatus.CANCELED).ensure_can_access(now)
