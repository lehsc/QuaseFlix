"""
Unit tests for the payment method domain models.

They do not touch the database or the API, so they run anywhere:
    PYTHONPATH=. pytest tests/test_payment_method_models.py
"""
from datetime import date, timedelta

import pytest

from backend.models.boleto import Boleto
from backend.models.credit_card import CreditCard
from backend.models.payment_method import PaymentMethod
from backend.models.payment_type import PaymentType

# Well-known test card number: it passes the Luhn check, but is not a real card.
VALID_CARD_NUMBER = "4111111111111111"


def make_card(**overrides) -> CreditCard:
    data = dict(
        account_id = 1,
        card_number = VALID_CARD_NUMBER,
        holder_name = "Maria da Silva",
        cvc = "123",
        expiration_month = 12,
        expiration_year = date.today().year + 2,
        bank_name = "Banco Exemplo",
    )
    data.update(overrides)
    return CreditCard(**data)


# ---------------------------------------------------------------- CreditCard

def test_credit_card_keeps_only_masked_number():
    card = make_card()

    assert card.payment_type == PaymentType.CREDIT_CARD
    assert card.last_four == "1111"
    assert card.masked_number == "************1111"


def test_credit_card_accepts_spaces_and_hyphens_in_number():
    assert make_card(card_number = "4111 1111 1111 1111").last_four == "1111"
    assert make_card(card_number = "4111-1111-1111-1111").last_four == "1111"


def test_credit_card_never_stores_full_number_or_cvc():
    card = make_card(cvc = "987")

    stored_values = [str(value) for value in vars(card).values()]
    assert VALID_CARD_NUMBER not in stored_values
    assert "987" not in stored_values
    assert VALID_CARD_NUMBER not in str(card.details())
    assert VALID_CARD_NUMBER not in str(card.summary())
    assert "cvc" not in card.details()
    assert "cvc" not in card.summary()


def test_credit_card_expiration_is_last_day_of_month():
    card = make_card(expiration_month = 2, expiration_year = date.today().year + 1)

    next_march_first = date(date.today().year + 1, 3, 1)
    assert card.expiration_date == next_march_first - timedelta(days = 1)


def test_credit_card_valid_through_end_of_current_month():
    today = date.today()

    card = make_card(expiration_month = today.month, expiration_year = today.year)

    assert card.expiration_date >= today


def test_credit_card_normalizes_holder_and_bank_names():
    card = make_card(holder_name = "  Maria   da  Silva ", bank_name = "  Banco X ")

    assert card.holder_name == "Maria da Silva"
    assert card.bank_name == "Banco X"


@pytest.mark.parametrize("bank_name", [None, "", "   "])
def test_credit_card_bank_name_is_optional(bank_name):
    assert make_card(bank_name = bank_name).bank_name is None


@pytest.mark.parametrize("card_number", [
    "4111111111111112",       # fails the Luhn check
    "1234",                   # too short
    "41111111111111111111",   # 20 digits: too long
    "4111 1111 1111 abcd",    # not only digits
    "",
])
def test_credit_card_rejects_invalid_number(card_number):
    with pytest.raises(ValueError):
        make_card(card_number = card_number)


def test_credit_card_rejects_non_string_number():
    with pytest.raises(ValueError):
        make_card(card_number = 4111111111111111)


@pytest.mark.parametrize("cvc", ["12", "12345", "abc", "", None])
def test_credit_card_rejects_invalid_cvc(cvc):
    with pytest.raises(ValueError, match = "CVC"):
        make_card(cvc = cvc)


@pytest.mark.parametrize("holder_name", ["", "   ", "A" * 101, None])
def test_credit_card_rejects_invalid_holder_name(holder_name):
    with pytest.raises(ValueError, match = "Holder name"):
        make_card(holder_name = holder_name)


def test_credit_card_rejects_long_bank_name():
    with pytest.raises(ValueError, match = "Bank name"):
        make_card(bank_name = "B" * 51)


@pytest.mark.parametrize("month", [0, 13, -1, "12", None])
def test_credit_card_rejects_invalid_expiration_month(month):
    with pytest.raises(ValueError, match = "month"):
        make_card(expiration_month = month)


@pytest.mark.parametrize("year_offset", [21, 100])
def test_credit_card_rejects_year_too_far_ahead(year_offset):
    with pytest.raises(ValueError, match = "year"):
        make_card(expiration_year = date.today().year + year_offset)


def test_credit_card_rejects_two_digit_year():
    with pytest.raises(ValueError, match = "year"):
        make_card(expiration_year = 30)


def test_credit_card_rejects_expired_card():
    today = date.today()
    last_month = today.month - 1 or 12
    year = today.year if today.month > 1 else today.year - 1

    with pytest.raises(ValueError, match = "expired"):
        make_card(expiration_month = last_month, expiration_year = year)


def test_credit_card_error_messages_do_not_leak_the_number():
    with pytest.raises(ValueError) as error:
        make_card(card_number = "4111111111111112")

    assert "4111111111111112" not in str(error.value)


# -------------------------------------------------------------------- Boleto

def test_boleto_issue_generates_barcode_and_due_date():
    boleto = Boleto.issue(account_id = 1)

    assert boleto.payment_type == PaymentType.BOLETO
    assert len(boleto.barcode) == Boleto.BARCODE_LENGTH
    assert boleto.barcode.isdigit()
    assert boleto.due_date == date.today() + timedelta(days = Boleto.DUE_DAYS)


def test_boleto_issue_generates_different_barcodes():
    assert Boleto.issue(1).barcode != Boleto.issue(1).barcode


@pytest.mark.parametrize("barcode", ["123", "1" * 46, "1" * 48, "a" * 47, "", None])
def test_boleto_rejects_invalid_barcode(barcode):
    with pytest.raises(ValueError, match = "barcode"):
        Boleto(1, barcode, date.today())


def test_boleto_rejects_due_date_in_the_past():
    with pytest.raises(ValueError, match = "past"):
        Boleto(1, "1" * 47, date.today() - timedelta(days = 1))


def test_boleto_rejects_due_date_that_is_not_a_date():
    with pytest.raises(ValueError, match = "date"):
        Boleto(1, "1" * 47, "2030-01-01")


# ------------------------------------------------------------ PaymentMethod

def test_payment_method_is_abstract():
    with pytest.raises(TypeError):
        PaymentMethod(1, PaymentType.BOLETO)


@pytest.mark.parametrize("account_id", [0, -1, "1", None, True, 1.5])
def test_payment_method_rejects_invalid_account_id(account_id):
    with pytest.raises(ValueError, match = "account_id"):
        Boleto(account_id, "1" * 47, date.today())


@pytest.mark.parametrize("payment_method, details_columns, summary_keys", [
    (make_card(), {"card_number", "holder_name", "expiration_date", "bank_name"},
     {"last_four", "holder_name", "expiration_date", "bank_name"}),
    (Boleto.issue(1), {"barcode", "due_date"}, {"barcode", "due_date"}),
])
def test_every_payment_method_describes_itself_polymorphically(
    payment_method, details_columns, summary_keys
):
    assert isinstance(payment_method, PaymentMethod)
    assert payment_method.account_id == 1
    assert set(payment_method.details()) == details_columns
    assert set(payment_method.summary()) == summary_keys
