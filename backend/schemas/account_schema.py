from pydantic import BaseModel
from datetime import date

# Schema for creating an account (incoming request data)
class AccountCreateSchema(BaseModel):
    email: str
    password_hash: str
    cpf: str
    birth_date: date
    phone: str
    address: str