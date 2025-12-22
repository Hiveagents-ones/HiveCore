from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Union, Dict, Any


class BaseCustomException(Exception):
    """Base class for custom exceptions."""

    def __init__(self, status_code: int, detail: str, headers: Union[Dict[str, str], None] = None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
        super().__init__(detail)


class AuthenticationError(BaseCustomException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


class AuthorizationError(BaseCustomException):
    """Raised when authorization fails."""

    def __init__(self, detail: str = "Authorization failed"):
        super().__init__(status_code=403, detail=detail)


class NotFoundError(BaseCustomException):
    """Raised when a resource is not found."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class ConflictError(BaseCustomException):
    """Raised when a conflict occurs (e.g., duplicate entry)."""

    def __init__(self, detail: str = "Conflict occurred"):
        super().__init__(status_code=409, detail=detail)


class UnprocessableEntityError(BaseCustomException):
    """Raised when the request is well-formed but unable to be processed."""

    def __init__(self, detail: str = "Unprocessable entity"):
        super().__init__(status_code=422, detail=detail)


class InternalServerError(BaseCustomException):
    """Raised for internal server errors."""

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(status_code=500, detail=detail)


def create_error_response(status_code: int, detail: str) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {"error": {"status_code": status_code, "detail": detail}}


async def custom_exception_handler(request: Request, exc: BaseCustomException) -> JSONResponse:
    """Handler for custom exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(status_code=exc.status_code, detail=exc.detail),
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]) -> JSONResponse:
    """Handler for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(status_code=exc.status_code, detail=exc.detail),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for request validation exceptions."""
    errors = exc.errors()
    error_details = [
        {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
        }
        for error in errors
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "status_code": 422,
                "detail": "Validation failed",
                "errors": error_details,
            }
        },
    )
