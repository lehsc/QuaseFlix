from backend.database.connection import get_db_connection
from backend.exceptions import AccountNotFoundError, InvalidCredentialsError
from backend.models.account_status import AccountStatus
from backend.models.authenticated_account import AuthenticatedAccount
from backend.security import burn_password_check, verify_password

# LOCALTIMESTAMP is read in the same query so "now" uses the same clock and time
# zone that filled created_at (a timestamp without time zone).
_SELECT_BY_EMAIL = """
    SELECT id, email, password_hash, status, plan_id, created_at, LOCALTIMESTAMP
    FROM public.account
    WHERE LOWER(email) = LOWER(%s)
    ORDER BY id
    LIMIT 1;
"""

_SELECT_BY_ID = """
    SELECT id, email, status, plan_id, created_at, LOCALTIMESTAMP
    FROM public.account
    WHERE id = %s;
"""


def _status_from_database(value: str | None) -> AccountStatus:
    # The database enum is upper case (TRIAL) and matches the enum member names.
    return AccountStatus[value] if value else AccountStatus.TRIAL


def authenticate(email: str, password: str) -> AuthenticatedAccount:
    """
    Checks the e-mail and password and returns the account.

    Raises InvalidCredentialsError when the e-mail is unknown or the password is
    wrong (the same error on purpose), AccountCanceledError for a canceled
    account and SubscriptionExpiredError when the free trial is over. The status
    is only checked after the password, so it is never revealed to someone who
    does not know it.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(_SELECT_BY_EMAIL, (email.strip(),))
            row = cursor.fetchone()

    if row is None:
        burn_password_check(password)
        raise InvalidCredentialsError()

    account_id, account_email, password_hash, status, plan_id, created_at, now = row
    if not verify_password(password, password_hash):
        raise InvalidCredentialsError()

    account = AuthenticatedAccount(
        account_id, account_email, _status_from_database(status), plan_id, created_at
    )
    account.ensure_can_access(now)
    return account


def get_account_for_access(account_id: int) -> AuthenticatedAccount:
    """
    Loads the account behind a valid token and checks that it may still use the
    service (it can have been canceled after the login).

    Raises AccountNotFoundError, AccountCanceledError or SubscriptionExpiredError.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(_SELECT_BY_ID, (account_id,))
            row = cursor.fetchone()

    if row is None:
        raise AccountNotFoundError(account_id)

    account_id, account_email, status, plan_id, created_at, now = row
    account = AuthenticatedAccount(
        account_id, account_email, _status_from_database(status), plan_id, created_at
    )
    account.ensure_can_access(now)
    return account
