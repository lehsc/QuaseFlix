from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


# Schemas for registering a payment method (incoming request data).
# The "type" field tells which schema applies (discriminated union).
class CreditCardCreateSchema(BaseModel):
    type: Literal["credit_card"]
    card_number: str
    holder_name: str
    cvc: str
    expiration_month: int
    expiration_year: int
    bank_name: Optional[str] = None


class BoletoCreateSchema(BaseModel):
    # The boleto is issued by the system, so nothing else is required.
    type: Literal["boleto"]


PaymentMethodCreateSchema = Annotated[
    Union[CreditCardCreateSchema, BoletoCreateSchema],
    Field(discriminator="type"),
]
