from psycopg import sql

from backend.database.connection import get_db_connection
from backend.exceptions import AccountNotFoundError
from backend.models.payment_method import PaymentMethod
from backend.models.payment_type import PaymentType

# Each payment type keeps its specific columns in its own details table.
_DETAILS_TABLES = {
    PaymentType.CREDIT_CARD: "credit_card_details",
    PaymentType.BOLETO: "boleto_details",
}


def register_payment_method(payment_method: PaymentMethod) -> int:
    """
    Persists a payment method (base row + details row) in a single transaction
    and returns the new payment_method id.

    Raises AccountNotFoundError if the account does not exist. Any other
    database error is propagated to the caller.
    """
    details = payment_method.details()
    details_table = _DETAILS_TABLES[payment_method.payment_type]

    # Table and column names come from this code (never from user input) and
    # are still quoted as identifiers; the values go through placeholders.
    columns = sql.SQL(", ").join(
        sql.Identifier(column) for column in ("payment_method_id", *details)
    )
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in range(len(details) + 1))
    insert_details = sql.SQL("INSERT INTO public.{table} ({columns}) VALUES ({values});").format(
        table=sql.Identifier(details_table),
        columns=columns,
        values=placeholders,
    )

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM public.account WHERE id = %s;",
                (payment_method.account_id,),
            )
            if cursor.fetchone() is None:
                raise AccountNotFoundError(payment_method.account_id)

            cursor.execute(
                "INSERT INTO public.payment_method (account_id, type) VALUES (%s, %s) RETURNING id;",
                (payment_method.account_id, payment_method.payment_type.value),
            )
            payment_method_id = cursor.fetchone()[0]

            cursor.execute(insert_details, (payment_method_id, *details.values()))

    return payment_method_id
