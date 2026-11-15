from enum import Enum

class PaymentType(Enum):
    # The values are stored in public.payment_method.type
    CREDIT_CARD = "credit_card"
    BOLETO = "boleto"
