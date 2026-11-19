"""Application errors that map cleanly onto HTTP responses."""


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFound(AppError):
    def __init__(self, message: str = "Not found"):
        super().__init__(message, 404)


class SQLValidationError(AppError):
    """Generated or user-edited SQL failed the safety checks."""

    def __init__(self, message: str):
        super().__init__(message, 422)


class ExecutionError(AppError):
    """Database rejected or failed the query. `message` is safe to show; `detail` is not."""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message, 422)
        self.detail = detail


class LLMError(AppError):
    def __init__(self, message: str):
        super().__init__(message, 502)
