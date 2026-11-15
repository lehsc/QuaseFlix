"""
Unit tests for the Plan domain model (no database or API needed):
    PYTHONPATH=. pytest tests/test_plan_models.py
"""
from decimal import Decimal

import pytest

from backend.models.plan import Plan


def test_plan_exposes_its_data():
    plan = Plan(1, "Padrão", Decimal("25.90"), "Acesso ilimitado ao catálogo.")

    assert plan.id == 1
    assert plan.name == "Padrão"
    assert plan.price == Decimal("25.90")
    assert plan.description == "Acesso ilimitado ao catálogo."


def test_plan_can_be_built_from_a_database_row():
    row = (2, "Premium", Decimal("39.90"), None)

    plan = Plan(*row)

    assert (plan.id, plan.name, plan.price, plan.description) == row


def test_plan_strips_name_and_description():
    plan = Plan(1, "  Padrão  ", Decimal("25.90"), "  Texto  ")

    assert plan.name == "Padrão"
    assert plan.description == "Texto"


@pytest.mark.parametrize("description", [None, "", "   "])
def test_plan_description_is_optional(description):
    assert Plan(1, "Padrão", Decimal("25.90"), description).description is None


def test_plan_can_be_free():
    assert Plan(1, "Grátis", Decimal("0")).price == Decimal("0")


@pytest.mark.parametrize("plan_id", [0, -1, "1", None, True, 1.5])
def test_plan_rejects_invalid_id(plan_id):
    with pytest.raises(ValueError, match = "plan_id"):
        Plan(plan_id, "Padrão", Decimal("25.90"))


@pytest.mark.parametrize("name", ["", "   ", "A" * 101, None])
def test_plan_rejects_invalid_name(name):
    with pytest.raises(ValueError, match = "name"):
        Plan(1, name, Decimal("25.90"))


@pytest.mark.parametrize("price", [
    Decimal("-0.01"),      # negative
    25.9,                  # float: money must be Decimal
    "25.90",               # string
    None,
    Decimal("NaN"),
    Decimal("Infinity"),
])
def test_plan_rejects_invalid_price(price):
    with pytest.raises(ValueError, match = "price"):
        Plan(1, "Padrão", price)
