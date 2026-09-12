from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


async def validation_error_handler(
    request: Request,
    error: ValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "details": error.errors()},
    )


async def request_validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "details": error.errors()},
    )


async def integrity_error_handler(
    request: Request,
    error: IntegrityError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": "conflict", "detail": "Resource already exists"},
    )
