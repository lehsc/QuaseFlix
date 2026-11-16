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


class InvalidCredentialsError(Exception):
    """Raised when the e-mail and password do not match any account."""

    def __init__(self):
        # Same message for "unknown e-mail" and "wrong password" on purpose, so
        # the answer never reveals which e-mails are registered.
        super().__init__("Invalid e-mail or password.")


class AccountCanceledError(Exception):
    """Raised when a canceled account tries to use the service."""

    def __init__(self, account_id: int):
        super().__init__("This account has been canceled.")
        self.account_id = account_id


class SubscriptionExpiredError(Exception):
    """Raised when the free trial is over and the account is not active."""

    def __init__(self, account_id: int):
        super().__init__("The free trial has ended and there is no active subscription.")
        self.account_id = account_id


class InvalidTokenError(Exception):
    """Raised when an access token is malformed, tampered with or expired."""


class MediaNotFoundError(Exception):
    """Raised when a work is not available in the catalog."""

    def __init__(self, media_id: int):
        super().__init__(f"Media {media_id} not found.")
        self.media_id = media_id
