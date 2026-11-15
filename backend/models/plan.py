from decimal import Decimal


class Plan:
    """Subscription plan that an account signs up for (see public.plan)."""

    MAX_NAME_LENGTH = 100

    def __init__(self, plan_id: int, name: str, price: Decimal, description: str | None = None):
        if isinstance(plan_id, bool) or not isinstance(plan_id, int) or plan_id <= 0:
            raise ValueError("plan_id must be a positive integer.")

        clean_name = name.strip() if isinstance(name, str) else ""
        if not clean_name:
            raise ValueError("Plan name is required.")
        if len(clean_name) > self.MAX_NAME_LENGTH:
            raise ValueError(f"Plan name must have at most {self.MAX_NAME_LENGTH} characters.")

        # Decimal (not float) so money is never rounded by binary arithmetic.
        if not isinstance(price, Decimal) or not price.is_finite() or price < 0:
            raise ValueError("Plan price must be a non-negative Decimal.")

        clean_description = description.strip() if isinstance(description, str) else None

        self.__id = plan_id
        self.__name = clean_name
        self.__price = price
        self.__description = clean_description or None

    @property
    def id(self) -> int:
        return self.__id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def price(self) -> Decimal:
        return self.__price

    @property
    def description(self) -> str | None:
        return self.__description
