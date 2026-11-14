import uuid
import pytest
from datetime import date
from backend.services.account import register_account
from backend.models.account import Account
from backend.models.account_status import AccountStatus


def test_registers_new_account_successfully():
    # Instantiate the Account object
    account = Account(
        email = f"user_{uuid.uuid4().hex[:8]}@quaseflix-test.com",
        password_hash = "fake_hashed_password_123",
        cpf = "12345678901",
        birth_date = date(1995, 5, 15),
        phone = "31999999999",
        address = "Rua Teste, 123",
        status = AccountStatus.TRIAL
    )
    
    valid_plan_id = 1 
    registration = register_account(account = account, plan_id = valid_plan_id)
    
    assert registration is True