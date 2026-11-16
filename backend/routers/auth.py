import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.exceptions import (
    AccountCanceledError,
    AccountNotFoundError,
    InvalidCredentialsError,
    InvalidTokenError,
    SubscriptionExpiredError,
)
from backend.models.authenticated_account import AuthenticatedAccount
from backend.schemas.auth_schema import LoginSchema
from backend.security import (
    ACCESS_TOKEN_TTL_SECONDS,
    create_access_token,
    decode_access_token,
)
from backend.services.auth_services import authenticate as service_authenticate
from backend.services.auth_services import (
    get_account_for_access as service_get_account_for_access,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix = "/api/auth",
    tags = ["Authentication"]
)

# auto_error=False: a missing header is answered by get_current_account, so the
# status code and message are the same for every authentication problem.
_bearer_scheme = HTTPBearer(auto_error = False)

_BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def get_current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedAccount:
    """
    Dependency for the endpoints that need a logged-in account (RF04):

        def my_endpoint(account: AuthenticatedAccount = Depends(get_current_account)):

    Answers 401 when the token is missing, invalid or expired, 403 when the
    account was canceled and 402 when its free trial is over.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers=_BEARER_CHALLENGE,
        )

    try:
        account_id = decode_access_token(credentials.credentials)
        return service_get_account_for_access(account_id)
    except (InvalidTokenError, AccountNotFoundError):
        # An account that no longer exists is the same as an invalid token.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers=_BEARER_CHALLENGE,
        )
    except AccountCanceledError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SubscriptionExpiredError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))
    except Exception:
        logger.exception("Unexpected error while validating the session.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to validate the session."
        )


@router.post("/login")
def api_login(payload: LoginSchema):
    try:
        account = service_authenticate(payload.email, payload.password)
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except AccountCanceledError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except SubscriptionExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except Exception:
        logger.exception("Unexpected error while logging in.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to log in."
        )

    return {
        "message": "Login successful!",
        "token": create_access_token(account.id),
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_TTL_SECONDS,
        "account": account.to_dict(),
    }


@router.get("/me")
def api_me(account: AuthenticatedAccount = Depends(get_current_account)):
    return {"account": account.to_dict()}
