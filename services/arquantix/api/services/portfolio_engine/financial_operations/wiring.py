"""Wiring runtime — Portfolio Financial Operation Guard sur chemins bundle."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.financial_operations.enums import PortfolioFinancialOperationType
from services.portfolio_engine.financial_operations.service import (
    AcquirePortfolioFinancialOperationResult,
    acquire_portfolio_financial_operation,
    release_portfolio_financial_operation,
)


def acquire_bundle_invest_portfolio_operation(
    db: Session,
    *,
    portfolio_id: UUID,
    batch_id: str,
) -> AcquirePortfolioFinancialOperationResult:
    return acquire_portfolio_financial_operation(
        db,
        portfolio_id=portfolio_id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=batch_id,
    )


def release_bundle_invest_portfolio_operation(
    db: Session,
    *,
    portfolio_id: UUID,
    batch_id: str,
    failed: bool = False,
) -> bool:
    from services.portfolio_engine.financial_operations.enums import (
        PortfolioFinancialOperationStatus,
    )

    terminal = (
        PortfolioFinancialOperationStatus.FAILED.value
        if failed
        else PortfolioFinancialOperationStatus.RELEASED.value
    )
    return release_portfolio_financial_operation(
        db,
        portfolio_id=portfolio_id,
        execution_id=batch_id,
        terminal_status=terminal,
    )


def acquire_bundle_rebalance_v3_portfolio_operation(
    db: Session,
    *,
    portfolio_id: UUID,
    execution_id: UUID,
) -> AcquirePortfolioFinancialOperationResult:
    return acquire_portfolio_financial_operation(
        db,
        portfolio_id=portfolio_id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_REBALANCE_V3,
        execution_id=execution_id,
    )


def release_bundle_rebalance_v3_portfolio_operation(
    db: Session,
    *,
    portfolio_id: UUID,
    execution_id: UUID,
    failed: bool = False,
) -> bool:
    from services.portfolio_engine.financial_operations.enums import (
        PortfolioFinancialOperationStatus,
    )

    terminal = (
        PortfolioFinancialOperationStatus.FAILED.value
        if failed
        else PortfolioFinancialOperationStatus.RELEASED.value
    )
    return release_portfolio_financial_operation(
        db,
        portfolio_id=portfolio_id,
        execution_id=execution_id,
        terminal_status=terminal,
    )


def acquire_bundle_withdraw_portfolio_operation(
    db: Session,
    *,
    portfolio_id: UUID,
    batch_id: str,
) -> AcquirePortfolioFinancialOperationResult:
    return acquire_portfolio_financial_operation(
        db,
        portfolio_id=portfolio_id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_WITHDRAW,
        execution_id=batch_id,
    )


def release_bundle_withdraw_portfolio_operation(
    db: Session,
    *,
    portfolio_id: UUID,
    batch_id: str,
    failed: bool = False,
) -> bool:
    from services.portfolio_engine.financial_operations.enums import (
        PortfolioFinancialOperationStatus,
    )

    terminal = (
        PortfolioFinancialOperationStatus.FAILED.value
        if failed
        else PortfolioFinancialOperationStatus.RELEASED.value
    )
    return release_portfolio_financial_operation(
        db,
        portfolio_id=portfolio_id,
        execution_id=batch_id,
        terminal_status=terminal,
    )
