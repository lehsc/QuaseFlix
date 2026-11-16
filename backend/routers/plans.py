import logging

from fastapi import APIRouter, HTTPException, status, Depends
from backend.routers.auth import get_current_account

from backend.exceptions import AccountNotFoundError, PlanNotFoundError
from backend.models.plan import Plan
from backend.schemas.plan_schema import PlanSelectSchema
from backend.services.plan_services import list_plans as service_list_plans
from backend.services.plan_services import select_plan as service_select_plan

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["Plans"])


def _plan_to_dict(plan: Plan) -> dict:
    return {
        "id": plan.id,
        "name": plan.name,
        "price": float(plan.price),
        "description": plan.description,
    }


@router.get("/api/plans")
def api_list_plans():
    try:
        plans = service_list_plans()
    except Exception:
        logger.exception("Unexpected error while listing plans.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to list plans."
        )
    return [_plan_to_dict(plan) for plan in plans]


@router.put("/api/accounts/{account_id}/plan")
def api_select_plan(account_id: int, payload: PlanSelectSchema, account = Depends(get_current_account)):
    if account.id != account_id:
        raise HTTPException(403, "Account access denied.")
    try:
        plan = service_select_plan(account_id, payload.plan_id)
    except (PlanNotFoundError, AccountNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception:
        logger.exception("Unexpected error while selecting a plan.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to select plan."
        )
    return {
        "message": "Plan selected successfully!",
        "plan": _plan_to_dict(plan),
    }
