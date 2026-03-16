from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class TrellisError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str = "An unexpected error occurred") -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(TrellisError):
    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(TrellisError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(TrellisError):
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(TrellisError):
    status_code = 409
    code = "CONFLICT"


class ValidationError(TrellisError):
    status_code = 422
    code = "VALIDATION_ERROR"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(TrellisError)
    async def trellis_error_handler(request: Request, exc: TrellisError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )
