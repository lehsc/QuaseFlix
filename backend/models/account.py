from datetime import date
from backend.models.account_status import AccountStatus

class Account:
    def __init__(self, email: str, password_hash: str, cpf: str, birth_date: date, phone: str, address: str, status: AccountStatus = AccountStatus.TRIAL):
        self.__email = email
        self.__password_hash = password_hash
        self.__cpf = cpf
        self.__birth_date = birth_date
        self.__phone = phone
        self.__address = address
        