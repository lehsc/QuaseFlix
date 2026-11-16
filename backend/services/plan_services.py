from backend.database.connection import get_db_connection
from backend.exceptions import AccountNotFoundError, PlanNotFoundError
from backend.models.plan import Plan

_PLAN_COLUMNS = "id, name, price, description"


def list_plans() -> list[Plan]:
    """Returns every available plan, cheapest first."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT {_PLAN_COLUMNS} FROM public.plan ORDER BY price, id;")
            rows = cursor.fetchall()
    return [Plan(*row) for row in rows]


def select_plan(account_id: int, plan_id: int) -> Plan:
    """
    Sets the plan of an account and returns it.

    Raises PlanNotFoundError or AccountNotFoundError when either does not
    exist (nothing is changed in that case).
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT {_PLAN_COLUMNS} FROM public.plan WHERE id = %s;",
                (plan_id,)
            )
            plan_row = cursor.fetchone()
            if plan_row is None:
                raise PlanNotFoundError(plan_id)

            cursor.execute(
                "UPDATE public.account SET plan_id = %s WHERE id = %s RETURNING id;",
                (plan_id, account_id)
            )
            if cursor.fetchone() is None:
                raise AccountNotFoundError(account_id)

    return Plan(*plan_row)
