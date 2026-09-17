from enum import IntEnum


class ApiErrorsCode(IntEnum):
    USER_ALREADY_EXISTS = 1000
    USER_NOT_FOUND = 1001
    FORBIDDEN = 1002
    RESOURCE_ACCESS_DENIED = 1003
    ROLE_NOT_FOUND = 1004

    MAX_MEDIA_SIZE = 2000
    MEDIA_NOT_FOUND = 2001
    INVALID_MEDIA_TYPE = 2002

    CATEGORY_ALREADY_EXISTS = 3000
    CATEGORY_NOT_FOUND = 3001
    INVALID_CATEGORY_FORM = 3002

    ARTICLE_ALREADY_EXISTS = 4000
    ARTICLE_NOT_FOUND = 4001
    INVALID_ARTICLE_STATE = 4002
    INVALID_ARTICLE_TRANSITION = 4003

    COMMENT_NOT_FOUND = 5000
    REACTION_NOT_FOUND = 5001


class ApiException(Exception):
    def __init__(self, status_code: int, error_code: int, message: str):
        super().__init__(message)
        self._status_code = status_code
        self._error_code = error_code
        self._message = message

    @property
    def message(self):
        return {"error_code": self._error_code, "message": self._message}

    @property
    def status_code(self):
        return self._status_code

    @property
    def error_code(self):
        return self._error_code

    @staticmethod
    def server_internal_error() -> dict:
        return {"error_code": 500, "message": "Internal server error"}
