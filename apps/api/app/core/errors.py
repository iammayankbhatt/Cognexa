"""Consistent error responses: {"error": {"code", "message", "request_id"}}."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)

_HTTP_CODES = {
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}


class AppError(Exception):
    """An expected error. `details` (optional) is added to the envelope as error.details;
    `headers` (optional) are sent with the response, e.g. Retry-After on 429."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        *,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.headers = headers


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    rid = request_id_ctx.get()
    error: dict[str, Any] = {"code": code, "message": message, "request_id": rid}
    if details:
        error["details"] = details
    return JSONResponse(
        status_code=status_code,
        content={"error": error},
        headers={"X-Request-ID": rid, **(headers or {})},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(
            exc.status_code, exc.code, exc.message, details=exc.details, headers=exc.headers
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(p) for p in first.get("loc", ()))
        return error_response(
            422, "validation_error", f"{loc}: {first.get('msg', 'invalid input')}"
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", exc_info=exc)
        return error_response(500, "internal_error", "Something went wrong.")
