from backend.models.account import Account
from backend.database.connection import get_db_connection

def register_account(account: Account, plan_id = 1) -> int | None:
    query = """
        INSERT INTO public.account (
            email, password_hash, cpf, birth_date, phone, address, plan_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """
        
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        account.email,
                        account.password_hash,
                        account.cpf,
                        account.birth_date,
                        account.phone,
                        account.address,     
                        plan_id                        
                    )
                )
                account_id = cursor.fetchone()[0]
        print(f"Conta {account.email} cadastrada com sucesso no banco de dados!")
        return account_id
    except Exception as e:
        print(f"Erro ao cadastrar conta: {e}")
        return None