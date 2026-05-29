"""Persistance idempotente des exécutions cost basis."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.cost_basis.models import CostBasisExecution
from services.cost_basis.valuation import FrozenExecutionValuation


class CostBasisExecutionRepository:
    def find_by_provider(
        self,
        db: Session,
        *,
        provider_source: str,
        provider_execution_id: str,
    ) -> Optional[CostBasisExecution]:
        return (
            db.query(CostBasisExecution)
            .filter(
                CostBasisExecution.provider_source == provider_source,
                CostBasisExecution.provider_execution_id == provider_execution_id,
            )
            .first()
        )

    def create(
        self,
        db: Session,
        *,
        client_id: UUID,
        person_id: Optional[UUID],
        position_asset: str,
        event_kind: str,
        quantity: Decimal,
        valuation: FrozenExecutionValuation,
        provider_source: str,
        provider_execution_id: str,
        tx_hash: Optional[str],
        counterparty_asset: Optional[str],
        portfolio_scope: Optional[str],
        portfolio_id: Optional[UUID],
        executed_at: datetime,
        metadata: Optional[dict[str, Any]] = None,
    ) -> CostBasisExecution:
        row = CostBasisExecution(
            client_id=client_id,
            person_id=person_id,
            position_asset=position_asset.upper(),
            event_kind=event_kind,
            quantity=quantity,
            native_quote_asset=valuation.native_quote_asset,
            native_execution_price=valuation.native_execution_price,
            native_notional=valuation.native_notional,
            execution_price_usdc=valuation.execution_price_usdc,
            execution_notional_usdc=valuation.execution_notional_usdc,
            execution_price_eur=valuation.execution_price_eur,
            execution_notional_eur=valuation.execution_notional_eur,
            eurusd_rate_at_execution=valuation.eurusd_rate_at_execution,
            fees_usdc=valuation.fees_usdc,
            fees_eur=valuation.fees_eur,
            provider_source=provider_source,
            provider_execution_id=provider_execution_id,
            tx_hash=tx_hash,
            counterparty_asset=counterparty_asset,
            portfolio_scope=portfolio_scope,
            portfolio_id=portfolio_id,
            metadata_=metadata or {},
            executed_at=executed_at,
        )
        db.add(row)
        db.flush()
        return row

    def list_for_client_asset(
        self,
        db: Session,
        client_id: UUID,
        asset: str,
        *,
        portfolio_scope: Optional[str] = None,
        portfolio_id: Optional[str] = None,
    ) -> list[CostBasisExecution]:
        q = db.query(CostBasisExecution).filter(
            CostBasisExecution.client_id == client_id,
            CostBasisExecution.position_asset == asset.upper(),
        )
        if portfolio_scope in (None, "global"):
            q = q.filter(
                (CostBasisExecution.portfolio_scope.is_(None))
                | (CostBasisExecution.portfolio_scope == "global")
                | (CostBasisExecution.portfolio_scope == "direct")
            )
        elif portfolio_scope == "direct":
            q = q.filter(CostBasisExecution.portfolio_scope == "direct")
        elif portfolio_scope == "bundle" and portfolio_id:
            q = q.filter(
                CostBasisExecution.portfolio_scope == "bundle",
                CostBasisExecution.portfolio_id == portfolio_id,
            )
        return q.order_by(CostBasisExecution.executed_at.asc()).all()
