"""Exceptions — Portfolio Financial Operation Guard (PR-4)."""
from __future__ import annotations

from uuid import UUID

PORTFOLIO_FINANCIAL_OPERATION_IN_PROGRESS_CODE = "portfolio_financial_operation_in_progress"

PORTFOLIO_FINANCIAL_OPERATION_USER_MESSAGE = (
    "A financial operation is already in progress on this portfolio. "
    "Please wait until it is completed."
)


class PortfolioFinancialOperationInProgress409(Exception):
    """Conflit : une opération financière est déjà active sur ce portefeuille."""

    http_status: int = 409

    def __init__(
        self,
        *,
        portfolio_id: UUID,
        existing_operation_type: str,
        existing_execution_id: UUID,
        requested_operation_type: str,
        requested_execution_id: UUID,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.existing_operation_type = existing_operation_type
        self.existing_execution_id = existing_execution_id
        self.requested_operation_type = requested_operation_type
        self.requested_execution_id = requested_execution_id
        super().__init__(PORTFOLIO_FINANCIAL_OPERATION_USER_MESSAGE)

    @property
    def error_code(self) -> str:
        return PORTFOLIO_FINANCIAL_OPERATION_IN_PROGRESS_CODE

    def to_response(self) -> dict:
        return {
            "status": "portfolio_financial_operation_in_progress",
            "error_code": self.error_code,
            "message": str(self),
            "portfolio_id": str(self.portfolio_id),
            "existing_operation_type": self.existing_operation_type,
            "requested_operation_type": self.requested_operation_type,
        }
