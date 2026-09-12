from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def _status_code_to_error_code(status_code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, "HTTP_ERROR")


def error_response(status_code: int, code: str, message: str, details: Any | None = None) -> JSONResponse:
    payload: dict[str, Any] = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def normalize_http_exception(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code") or _status_code_to_error_code(exc.status_code)
        message = detail.get("message") or detail.get("detail") or "Request failed"
        details = detail.get("details")
        return error_response(exc.status_code, code, message, details)
    if isinstance(detail, list):
        return error_response(exc.status_code, _status_code_to_error_code(exc.status_code), "Request failed", detail)
    return error_response(exc.status_code, _status_code_to_error_code(exc.status_code), str(detail) or "Request failed")
