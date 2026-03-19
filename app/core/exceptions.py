from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class TrellisError(Exception):
    """Base class for all domain errors.

    Subclasses declare their HTTP status code and machine-readable `code` as class
    attributes so the exception handler below can render a consistent JSON envelope
    without needing separate try/except blocks in every route.
    """
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str = "An unexpected error occurred") -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(TrellisError):
    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(TrellisError):
    # 401 = unauthenticated; used for missing/invalid tokens and bad credentials
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(TrellisError):
    # 403 = authenticated but not permitted to access the resource
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(TrellisError):
    # 409 = request conflicts with existing state (e.g. duplicate email on register)
    status_code = 409
    code = "CONFLICT"


class ValidationError(TrellisError):
    # Prefer Pydantic's built-in 422 for input validation; this is for domain-level rule violations
    status_code = 422
    code = "VALIDATION_ERROR"


def register_exception_handlers(app: FastAPI) -> None:
    # Single handler for all TrellisError subclasses — keeps routes free of error-format boilerplate
    @app.exception_handler(TrellisError)
    async def trellis_error_handler(request: Request, exc: TrellisError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )
