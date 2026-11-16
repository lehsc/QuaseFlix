from fastapi import APIRouter, HTTPException, status
from backend.schemas.account_schema import AccountCreateSchema # Your Pydantic schema
from backend.models.account import Account
from backend.security import hash_password
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
            password_hash = hash_password(payload.password),
            cpf = payload.cpf,
            birth_date = payload.birth_date,
            phone = payload.phone,
            address = payload.address,
        )
        account_id = service_register_account(account)
        if not account_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to register account."
            )
        return {
            "message": "Account registered successfully!",
            "id": account_id,
            "email": account.email
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )