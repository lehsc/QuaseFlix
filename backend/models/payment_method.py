from abc import ABC, abstractmethod

from backend.models.payment_type import PaymentType


class PaymentMethod(ABC):
    """
    Abstract base class for every way an account can pay for its subscription.

    Each concrete method (credit card, boleto, ...) validates its own data and
    describes itself through two polymorphic operations:
      - details(): columns persisted in the method's own details table;
      - summary(): non-sensitive data that may be returned by the API.
    """

    def __init__(self, account_id: int, payment_type: PaymentType):
        if isinstance(account_id, bool) or not isinstance(account_id, int) or account_id <= 0:
            raise ValueError("account_id must be a positive integer.")
        self.__account_id = account_id
        self.__payment_type = payment_type

    @property
    def account_id(self) -> int:
        return self.__account_id

    @property
    def payment_type(self) -> PaymentType:
        return self.__payment_type

    @abstractmethod
    def details(self) -> dict:
        """Mapping column -> value for this method's details table."""

    @abstractmethod
    def summary(self) -> dict:
        """Non-sensitive, JSON-friendly data about this method."""
