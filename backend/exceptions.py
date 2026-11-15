class AccountNotFoundError(Exception):
    """Raised when an operation references an account that does not exist."""

    def __init__(self, account_id: int):
        super().__init__(f"Account {account_id} not found.")
        self.account_id = account_id


class PlanNotFoundError(Exception):
    """Raised when an operation references a plan that does not exist."""

    def __init__(self, plan_id: int):
        super().__init__(f"Plan {plan_id} not found.")
        self.plan_id = plan_id
