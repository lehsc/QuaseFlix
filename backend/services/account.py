from backend.models.account import Account
from backend.database.connection import get_db_connection

def register_account(account: Account, plan_id) -> bool:      
    query = """
        INSERT INTO public.account (
            email, password_hash, cpf, birth_date, phone, address, status, plan_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
        
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        account._email,
                        account._password_hash,
                        account._cpf,
                        account._birth_date,
                        account._phone,
                        account._address,
                        account._status.value,      
                        plan_id                        
                    )
                )
        print(f"Conta {account._email} cadastrada com sucesso no banco de dados!")
        return True
    except Exception as e:
        print(f"Erro ao cadastrar conta: {e}")
        return False