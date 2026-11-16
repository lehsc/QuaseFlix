from datetime import date
from backend.models.account_status import AccountStatus

class Account:
    def __init__(self, email: str, password_hash: str, cpf: str, birth_date: date, phone: str | None, address: str):
        self.__email = email
        self.__password_hash = password_hash
        self.__cpf = cpf
        self.__birth_date = birth_date
        self.__phone = phone
        self.__address = address
        self.__status = AccountStatus.TRIAL

    @property
    def email(self) -> str:
        return self.__email

    @property
    def password_hash(self) -> str:
        return self.__password_hash

    @property
    def cpf(self) -> str:
        return self.__cpf

    @property
    def birth_date(self) -> date:
        return self.__birth_date

    @property
    def phone(self) -> str | None:
        return self.__phone

    @property
    def address(self) -> str:
        return self.__address

    @property
    def status(self) -> AccountStatus:
        return self.__status
