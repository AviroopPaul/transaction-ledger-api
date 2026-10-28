from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.shared.errors import BusinessRuleError, ConflictError, DomainError, NotFoundError

STATUS_BY_ERROR_TYPE: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    BusinessRuleError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details or {}}}
    return JSONResponse(status_code=status_code, content=body)


def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    status_code = status.HTTP_400_BAD_REQUEST
    for error_type, code in STATUS_BY_ERROR_TYPE.items():
        if isinstance(error, error_type):
            status_code = code
    return error_response(status_code, error.code, error.message, error.details)


def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
        for item in error.errors()
    ]
    return error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "VALIDATION_ERROR",
        "The request data is not valid.",
        {"fields": fields},
    )


def handle_http_error(request: Request, error: HTTPException) -> JSONResponse:
    return error_response(error.status_code, "HTTP_ERROR", str(error.detail))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_error)
