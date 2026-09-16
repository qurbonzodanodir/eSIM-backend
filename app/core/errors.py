from fastapi import Request
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


def _serializable_errors(errors: list[dict]) -> list[dict]:
    result = []
    for item in errors:
        result.append(
            {
                key: (
                    [_serialize_value(value) for value in value]
                    if isinstance(value, list)
                    else _serialize_value(value)
                )
                for key, value in item.items()
            }
        )
    return result


def _serialize_value(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    return str(value)


async def http_exception_handler(
    request: Request,
    error: HTTPException,
) -> JSONResponse:
    content = {
        "error": "http_error",
        "detail": error.detail,
    }
    return JSONResponse(
        status_code=error.status_code,
        content=content,
        headers=error.headers,
    )


async def validation_error_handler(
    request: Request,
    error: ValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "details": _serializable_errors(error.errors()),
        },
    )


async def request_validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "details": _serializable_errors(error.errors()),
        },
    )


async def integrity_error_handler(
    request: Request,
    error: IntegrityError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": "conflict", "detail": "Resource already exists"},
    )
