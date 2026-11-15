from fastapi import APIRouter, HTTPException, status
from backend.schemas.account_schema import AccountCreateSchema # Your Pydantic schema
from backend.models.account import Account
from backend.services.account_services import register_account as service_register_account

router = APIRouter(
    prefix = "/api/accounts",
    tags = ["Accounts"] # Groups endpoints neatly in FastAPI's Swagger docs
)

@router.post("/", status_code = status.HTTP_201_CREATED)
def api_register_account(payload: AccountCreateSchema):
    try:
        account = Account(
            email = payload.email,
            password_hash = payload.password_hash,
            cpf = payload.cpf,
            birth_date = payload.birth_date,
            phone = payload.phone,
            address = payload.address,
        )
        service_register_account(account)
        return {
            "message": "Account registered successfully!",
            "email": account.email
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )