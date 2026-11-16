from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.exceptions import AccountCanceledError, SubscriptionExpiredError
from backend.models.account_status import AccountStatus

# Length of the free trial, counted from the day the account was created.
TRIAL_DAYS = 30


@dataclass(frozen = True)
class AuthenticatedAccount:
    """
    The data of an account that proved its identity (login or valid token).

    It never carries the password hash. It also knows whether the account may
    use the service right now: ensure_can_access() applies that rule.
    """

    id: int
    email: str
    status: AccountStatus
    plan_id: int | None
    created_at: datetime | None

    @property
    def trial_ends_at(self) -> datetime | None:
        if self.created_at is None:
            return None
        return self.created_at + timedelta(days = TRIAL_DAYS)

    def ensure_can_access(self, now: datetime) -> None:
        """
        Raises AccountCanceledError for a canceled account, and
        SubscriptionExpiredError when the trial is over and the account never
        became active. Does nothing when the account may log in.
        """
        if self.status == AccountStatus.CANCELED:
            raise AccountCanceledError(self.id)
        if (
            self.status == AccountStatus.TRIAL
            and self.trial_ends_at is not None
            and now >= self.trial_ends_at
        ):
            raise SubscriptionExpiredError(self.id)

    def to_dict(self) -> dict:
        """Non-sensitive, JSON-friendly data returned by the API."""
        return {
            "id": self.id,
            "email": self.email,
            "status": self.status.value,
            "plan_id": self.plan_id,
        }
