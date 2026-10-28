from typing import Any


class DomainError(Exception):
    code = "DOMAIN_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class BusinessRuleError(DomainError):
    pass
