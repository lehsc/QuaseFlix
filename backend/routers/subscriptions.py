from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from backend.security import decode_access_token, create_access_token
from backend.exceptions import InvalidTokenError, InvalidCredentialsError
from backend.database.connection import get_db_connection
from backend.schemas.auth_schema import LoginSchema
from backend.services.auth_services import authenticate
from backend.services.subscription_services import manage

router = APIRouter(prefix='/api/subscription', tags=['Subscription'])
bearer = HTTPBearer(auto_error=False)


def owner(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials:
        raise HTTPException(401, 'Authentication required.')
    try:
        account_id = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(401, 'Invalid session.')
    with get_db_connection() as conn:
        if not conn.execute('SELECT 1 FROM public.account WHERE id=%s', (account_id,)).fetchone():
            raise HTTPException(401, 'Account not found.')
    return account_id


@router.post('/login')
def management_login(data: LoginSchema):
    try:
        account = authenticate(data.email, data.password, require_access=False)
    except InvalidCredentialsError:
        raise HTTPException(401, 'Invalid email or password.')
    return {'token': create_access_token(account.id)}


@router.get('')
def subscription(account_id: int = Depends(owner)):
    return manage(account_id)


class Payment(BaseModel):
    payment_method_id: int = Field(gt=0)


@router.post('/pay')
def pay(data: Payment, account_id: int = Depends(owner)):
    return manage(account_id, 'pay', data.payment_method_id)


@router.post('/cancel')
def cancel(account_id: int = Depends(owner)):
    return manage(account_id, 'cancel')


@router.post('/restore')
def restore(account_id: int = Depends(owner)):
    return manage(account_id, 'restore')


from backend.schemas.payment_method_schema import PaymentMethodCreateSchema


@router.post('/payment-methods', status_code=201)
def add_payment_method(data: PaymentMethodCreateSchema, account_id: int = Depends(owner)):
    from types import SimpleNamespace
    from backend.routers.payment_methods import api_register_payment_method
    return api_register_payment_method(account_id, data, SimpleNamespace(id=account_id))
