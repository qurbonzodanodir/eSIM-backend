from enum import StrEnum


class KycStatus(StrEnum):
    NOT_VERIFIED = "NOT_VERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
