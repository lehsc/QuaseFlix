from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])

@router.post("/")
def api_register_account():
    raise HTTPException(410, "Use /api/registration to complete verified registration.")
