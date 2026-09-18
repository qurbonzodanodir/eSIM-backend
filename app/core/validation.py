from typing import Annotated
from uuid import UUID

import phonenumbers
from pydantic import AfterValidator, BeforeValidator, Field, StringConstraints


def uppercase_code(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


def normalize_phone(value: str) -> str:
    if not value.startswith("+"):
        raise ValueError("Phone number must use international format")
    try:
        parsed = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException as error:
        raise ValueError("Invalid phone number") from error
    if parsed.extension or not phonenumbers.is_valid_number(parsed):
        raise ValueError("Invalid phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def normalize_guid(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as error:
        raise ValueError("Must be a valid UUID") from error


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
SearchText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CountryCode = Annotated[
    str, StringConstraints(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"),
    BeforeValidator(uppercase_code),
]
CurrencyCode = Annotated[
    str, StringConstraints(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"),
    BeforeValidator(uppercase_code),
]
PhoneNumber = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=7, max_length=20),
    AfterValidator(normalize_phone),
]
BundleGuid = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=36),
    AfterValidator(normalize_guid),
]
PageNumber = Annotated[int, Field(ge=1, le=1_000_000)]
PageSize = Annotated[int, Field(ge=1, le=100)]
