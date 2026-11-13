from enum import Enum

class AccountStatus(Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    CANCELED = "canceled"