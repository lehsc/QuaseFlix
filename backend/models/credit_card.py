import calendar
import re
from datetime import date

from backend.models.payment_method import PaymentMethod
from backend.models.payment_type import PaymentType


class CreditCard(PaymentMethod):
    """
    Credit card payment method.

    The full card number and the CVC are validated and then discarded: the
    object only keeps the masked number (every digit but the last four), so
    neither value can leak through the database, logs or API responses.
    """

    MAX_YEARS_AHEAD = 20
    MAX_HOLDER_NAME_LENGTH = 100
    MAX_BANK_NAME_LENGTH = 50

    def __init__(
        self,
        account_id: int,
        card_number: str,
        holder_name: str,
        cvc: str,
        expiration_month: int,
        expiration_year: int,
        bank_name: str | None = None,
    ):
        super().__init__(account_id, PaymentType.CREDIT_CARD)
        number = self._validate_card_number(card_number)
        self._validate_cvc(cvc)  # validated only, never stored
        self.__last_four = number[-4:]
        self.__masked_number = "*" * (len(number) - 4) + self.__last_four
        self.__holder_name = self._validate_holder_name(holder_name)
        self.__expiration_date = self._validate_expiration(expiration_month, expiration_year)
        self.__bank_name = self._validate_bank_name(bank_name)

    # ---- Validation helpers -------------------------------------------------

    @staticmethod
    def _passes_luhn(number: str) -> bool:
        total = 0
        for index, char in enumerate(reversed(number)):
            digit = int(char)
            if index % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0

    @classmethod
    def _validate_card_number(cls, card_number: str) -> str:
        if not isinstance(card_number, str):
            raise ValueError("Card number must be a string of digits.")
        number = re.sub(r"[\s-]", "", card_number)
        if not re.fullmatch(r"\d{13,19}", number, re.ASCII):
            raise ValueError("Card number must have between 13 and 19 digits.")
        if not cls._passes_luhn(number):
            raise ValueError("Invalid card number.")
        return number

    @staticmethod
    def _validate_cvc(cvc: str) -> None:
        if not isinstance(cvc, str) or not re.fullmatch(r"\d{3,4}", cvc, re.ASCII):
            raise ValueError("CVC must have 3 or 4 digits.")

    @classmethod
    def _validate_holder_name(cls, holder_name: str) -> str:
        name = " ".join(holder_name.split()) if isinstance(holder_name, str) else ""
        if not name:
            raise ValueError("Holder name is required.")
        if len(name) > cls.MAX_HOLDER_NAME_LENGTH:
            raise ValueError(f"Holder name must have at most {cls.MAX_HOLDER_NAME_LENGTH} characters.")
        return name

    @classmethod
    def _validate_expiration(cls, month: int, year: int) -> date:
        today = date.today()
        if isinstance(month, bool) or not isinstance(month, int) or not 1 <= month <= 12:
            raise ValueError("Expiration month must be between 1 and 12.")
        if (
            isinstance(year, bool)
            or not isinstance(year, int)
            or not 1000 <= year <= today.year + cls.MAX_YEARS_AHEAD
        ):
            raise ValueError("Invalid expiration year.")
        # A card is valid through the last day of its expiration month.
        expiration = date(year, month, calendar.monthrange(year, month)[1])
        if expiration < today:
            raise ValueError("Card is expired.")
        return expiration

    @classmethod
    def _validate_bank_name(cls, bank_name: str | None) -> str | None:
        if bank_name is None:
            return None
        name = bank_name.strip()
        if not name:
            return None
        if len(name) > cls.MAX_BANK_NAME_LENGTH:
            raise ValueError(f"Bank name must have at most {cls.MAX_BANK_NAME_LENGTH} characters.")
        return name

    # ---- Read-only properties ----------------------------------------------

    @property
    def last_four(self) -> str:
        return self.__last_four

    @property
    def masked_number(self) -> str:
        return self.__masked_number

    @property
    def holder_name(self) -> str:
        return self.__holder_name

    @property
    def expiration_date(self) -> date:
        return self.__expiration_date

    @property
    def bank_name(self) -> str | None:
        return self.__bank_name

    # ---- PaymentMethod contract --------------------------------------------

    def details(self) -> dict:
        return {
            "card_number": self.__masked_number,
            "holder_name": self.__holder_name,
            "expiration_date": self.__expiration_date,
            "bank_name": self.__bank_name,
        }

    def summary(self) -> dict:
        return {
            "last_four": self.__last_four,
            "holder_name": self.__holder_name,
            "expiration_date": self.__expiration_date.isoformat(),
            "bank_name": self.__bank_name,
        }
