from pydantic import BaseModel, Field
from datetime import date

# Schema for creating an account (incoming request data)
class AccountCreateSchema(BaseModel):
    email: str
    # The plain password only exists in this request: the router hashes it
    # before anything is stored (see backend/security.py).
    password: str = Field(min_length = 6, max_length = 128)
    cpf: str
    birth_date: date
    phone: str
    address: str
