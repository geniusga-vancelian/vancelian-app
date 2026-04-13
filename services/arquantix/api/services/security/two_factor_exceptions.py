"""2FA domain exceptions (shared across security.two_factor* modules)."""


class TwoFactorException(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)
