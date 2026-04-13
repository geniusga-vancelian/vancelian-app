"""Erreurs métier pour la route PDF relevé d'opération (PR1 — observabilité)."""

from __future__ import annotations


class OperationStatementHttpError(Exception):
    """Erreur métier mappée en réponse HTTP par la route ``operation-statement.pdf``."""

    __slots__ = ("code", "message", "status_code")

    def __init__(self, code: str, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
