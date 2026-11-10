"""Safe API errors: code + applicant/customer-safe message. Never raw supplier exceptions."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers or {}


def not_found() -> ApiError:
    return ApiError(404, "not_found", "Resource not found.")


def unauthenticated() -> ApiError:
    return ApiError(401, "unauthenticated", "Valid credentials are required.")


def forbidden(message: str = "This credential is not permitted to perform this action.") -> ApiError:
    return ApiError(403, "forbidden", message)


def conflict(code: str, message: str) -> ApiError:
    return ApiError(409, code, message)


def invalid(code: str, message: str) -> ApiError:
    return ApiError(400, code, message)
