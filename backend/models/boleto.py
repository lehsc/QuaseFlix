import secrets
from datetime import date, timedelta

from backend.models.payment_method import PaymentMethod
from backend.models.payment_type import PaymentType


class Boleto(PaymentMethod):
    """
    Boleto payment method.

    The customer does not type anything: the system issues the boleto, so a new
    one is normally created through Boleto.issue(). The barcode is simulated
    (random digits), which is enough for this project.
    """

    BARCODE_LENGTH = 47
    DUE_DAYS = 3

    def __init__(self, account_id: int, barcode: str, due_date: date):
        super().__init__(account_id, PaymentType.BOLETO)
        if not (
            isinstance(barcode, str)
            and barcode.isascii()
            and barcode.isdigit()
            and len(barcode) == self.BARCODE_LENGTH
        ):
            raise ValueError(f"Boleto barcode must have {self.BARCODE_LENGTH} digits.")
        if not isinstance(due_date, date):
            raise ValueError("Boleto due date must be a date.")
        if due_date < date.today():
            raise ValueError("Boleto due date cannot be in the past.")
        self.__barcode = barcode
        self.__due_date = due_date

    @classmethod
    def issue(cls, account_id: int) -> "Boleto":
        """Issues a new boleto that is due in DUE_DAYS days."""
        barcode = "".join(secrets.choice("0123456789") for _ in range(cls.BARCODE_LENGTH))
        return cls(account_id, barcode, date.today() + timedelta(days=cls.DUE_DAYS))

    @property
    def barcode(self) -> str:
        return self.__barcode

    @property
    def due_date(self) -> date:
        return self.__due_date

    def details(self) -> dict:
        return {
            "barcode": self.__barcode,
            "due_date": self.__due_date,
        }

    def summary(self) -> dict:
        return {
            "barcode": self.__barcode,
            "due_date": self.__due_date.isoformat(),
        }
