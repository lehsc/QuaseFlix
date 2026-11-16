import logging

from fastapi import APIRouter, HTTPException, status, Depends
from backend.routers.auth import get_current_account

from backend.exceptions import AccountNotFoundError
from backend.models.boleto import Boleto
from backend.models.credit_card import CreditCard
from backend.models.payment_method import PaymentMethod
from backend.schemas.payment_method_schema import (
    CreditCardCreateSchema,
    PaymentMethodCreateSchema,
)
from backend.services.payment_method_services import (
    register_payment_method as service_register_payment_method,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix = "/api/accounts/{account_id}/payment-methods",
    tags = ["Payment Methods"]
)


def _build_payment_method(account_id: int, payload: PaymentMethodCreateSchema) -> PaymentMethod:
    """Maps the request schema to the matching domain object (validates it)."""
    if isinstance(payload, CreditCardCreateSchema):
        return CreditCard(
            account_id = account_id,
            card_number = payload.card_number,
            holder_name = payload.holder_name,
            cvc = payload.cvc,
            expiration_month = payload.expiration_month,
            expiration_year = payload.expiration_year,
            bank_name = payload.bank_name,
        )
    return Boleto.issue(account_id)


@router.post("", status_code = status.HTTP_201_CREATED)
def api_register_payment_method(account_id: int, payload: PaymentMethodCreateSchema, account = Depends(get_current_account)):
    if account.id != account_id:
        raise HTTPException(403, "Account access denied.")
    try:
        payment_method = _build_payment_method(account_id, payload)
        payment_method_id = service_register_payment_method(payment_method)
    except ValueError as e:
        # Business rule violated (invalid card number, expired card, ...).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except AccountNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception:
        logger.exception("Unexpected error while registering a payment method.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register payment method."
        )

    return {
        "message": "Payment method registered successfully!",
        "id": payment_method_id,
        "type": payment_method.payment_type.value,
        **payment_method.summary(),
    }
