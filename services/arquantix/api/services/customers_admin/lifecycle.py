"""Actions admin sur l’identité client : gel connexion, suppression définitive."""
from __future__ import annotations

import logging
import os
import re
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import AdminUser, AuthMobileLoginOtpChallenge, Person
from services.portfolio_engine.clients.models import Client as PeClient

logger = logging.getLogger(__name__)


def _norm_phone_e164(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    t = re.sub(r"\s+", "", str(raw).strip())
    if not t.startswith("+"):
        t = "+" + t.lstrip("+")
    return t


def _admin_email_protected() -> str:
    return (os.getenv("ADMIN_EMAIL") or "admin@arquantix.com").strip().lower()


def set_person_login_frozen(db: Session, person_id: UUID, *, frozen: bool) -> bool:
    """Met ``persons.login_frozen``. Retourne False si personne absente."""
    p = db.query(Person).filter(Person.id == person_id).first()
    if p is None:
        return False
    p.login_frozen = frozen
    db.commit()
    return True


def _reject_if_protected_admin(db: Session, person_id: UUID) -> None:
    from fastapi import HTTPException, status

    prot = _admin_email_protected()
    u = db.query(AdminUser).filter(AdminUser.person_id == person_id).first()
    if u is not None and (u.email or "").strip().lower() == prot:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette identité est liée au compte administrateur système — action interdite.",
        )


def wipe_customer_data(db: Session, person_id: UUID) -> dict[str, Any]:
    """Supprime l’activité et l’identité client (person_id). Transaction unique."""
    from fastapi import HTTPException, status

    _reject_if_protected_admin(db, person_id)

    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    pe = db.query(PeClient).filter(PeClient.person_id == person_id).first()
    client_id = pe.id if pe else None
    report: dict[str, Any] = {"person_id": str(person_id), "client_id": str(client_id) if client_id else None}

    cid = str(client_id) if client_id else None

    def ex(sql: str, label: str) -> int:
        try:
            r = db.execute(text(sql), {"cid": cid, "pid": str(person_id)})
            n = r.rowcount
            report[label] = n if n is not None else 0
            return n or 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s: %s", label, exc)
            report[label] = f"error: {exc}"
            raise

    try:
        if cid:
            ex(
                """
                DELETE FROM pool_allocations WHERE supply_commitment_id IN (
                    SELECT id FROM pool_supply_commitments WHERE client_id = CAST(:cid AS uuid)
                ) OR borrow_position_id IN (
                    SELECT id FROM pool_borrow_positions WHERE client_id = CAST(:cid AS uuid)
                )
                """,
                "pool_allocations",
            )
            ex("DELETE FROM pool_supply_commitments WHERE client_id = CAST(:cid AS uuid)", "pool_supply_commitments")
            ex("DELETE FROM pool_borrow_positions WHERE client_id = CAST(:cid AS uuid)", "pool_borrow_positions")
            ex(
                "DELETE FROM borrower_interest_accruals WHERE loan_id IN (SELECT id FROM loans WHERE lender_client_id = CAST(:cid AS uuid) OR borrower_client_id = CAST(:cid AS uuid))",
                "borrower_interest_accruals",
            )
            ex(
                "DELETE FROM lender_interest_accruals WHERE loan_id IN (SELECT id FROM loans WHERE lender_client_id = CAST(:cid AS uuid) OR borrower_client_id = CAST(:cid AS uuid))",
                "lender_interest_accruals",
            )
            ex("DELETE FROM loans WHERE lender_client_id = CAST(:cid AS uuid) OR borrower_client_id = CAST(:cid AS uuid)", "loans")
            ex(
                "DELETE FROM investment_envelope_entries WHERE envelope_id IN (SELECT id FROM investment_envelopes WHERE client_id = CAST(:cid AS uuid))",
                "investment_envelope_entries",
            )
            ex("DELETE FROM investment_envelopes WHERE client_id = CAST(:cid AS uuid)", "investment_envelopes")
            ex("DELETE FROM notifications WHERE client_id = CAST(:cid AS uuid)", "notifications")
            ex("DELETE FROM price_alerts WHERE client_id = CAST(:cid AS uuid)", "price_alerts")
            ex("DELETE FROM client_favorites WHERE client_id = CAST(:cid AS uuid)", "client_favorites")
            ex("DELETE FROM exchange_orders WHERE client_id = CAST(:cid AS uuid)", "exchange_orders")
            ex("DELETE FROM crypto_positions WHERE client_id = CAST(:cid AS uuid)", "crypto_positions")
            ex(
                """
                DELETE FROM pe_settlement_instructions WHERE order_id IN (
                    SELECT id FROM pe_orders WHERE client_id = CAST(:cid AS uuid)
                ) OR trade_id IN (
                    SELECT id FROM pe_trades WHERE order_id IN (
                        SELECT id FROM pe_orders WHERE client_id = CAST(:cid AS uuid)
                    )
                ) OR from_account_id IN (
                    SELECT id FROM pe_ledger_accounts WHERE client_id = CAST(:cid AS uuid)
                ) OR to_account_id IN (
                    SELECT id FROM pe_ledger_accounts WHERE client_id = CAST(:cid AS uuid)
                )
                """,
                "pe_settlement_instructions",
            )
            ex(
                "DELETE FROM pe_trades WHERE order_id IN (SELECT id FROM pe_orders WHERE client_id = CAST(:cid AS uuid))",
                "pe_trades",
            )
            ex(
                "DELETE FROM pe_execution_instructions WHERE order_id IN (SELECT id FROM pe_orders WHERE client_id = CAST(:cid AS uuid))",
                "pe_execution_instructions",
            )
            ex("DELETE FROM pe_orders WHERE client_id = CAST(:cid AS uuid)", "pe_orders")
            ex(
                "DELETE FROM pe_ledger_entries WHERE account_id IN (SELECT id FROM pe_ledger_accounts WHERE client_id = CAST(:cid AS uuid))",
                "pe_ledger_entries",
            )
            ex(
                "DELETE FROM custody_webhook_events WHERE linked_transaction_id IN (SELECT id FROM custody_transactions WHERE account_id IN (SELECT id FROM custody_accounts WHERE client_id = CAST(:cid AS uuid)))",
                "custody_webhook_events",
            )
            ex(
                "DELETE FROM custody_transactions WHERE account_id IN (SELECT id FROM custody_accounts WHERE client_id = CAST(:cid AS uuid))",
                "custody_transactions",
            )
            ex(
                "DELETE FROM custody_account_balances WHERE account_id IN (SELECT id FROM custody_accounts WHERE client_id = CAST(:cid AS uuid))",
                "custody_account_balances",
            )
            ex("DELETE FROM custody_accounts WHERE client_id = CAST(:cid AS uuid)", "custody_accounts")
            ex("DELETE FROM pe_portfolios WHERE client_id = CAST(:cid AS uuid)", "pe_portfolios")
            ex("DELETE FROM pe_ledger_accounts WHERE client_id = CAST(:cid AS uuid)", "pe_ledger_accounts")
            ex("DELETE FROM pe_product_subscriptions WHERE client_id = CAST(:cid AS uuid)", "pe_product_subscriptions")
            ex("DELETE FROM pe_clients WHERE id = CAST(:cid AS uuid)", "pe_clients")

        ex("DELETE FROM documents WHERE person_id = CAST(:pid AS uuid)", "documents")
        ex("DELETE FROM audit_events WHERE person_id = CAST(:pid AS uuid)", "audit_events")
        ex("DELETE FROM registration_sessions WHERE person_id = CAST(:pid AS uuid)", "registration_sessions")
        ex("DELETE FROM two_factor_challenges WHERE person_id = CAST(:pid AS uuid)", "two_factor_challenges")

        au = db.query(AdminUser).filter(AdminUser.person_id == person_id).all()
        phones: set[str] = set()
        for u in au:
            n = _norm_phone_e164(u.mobile_e164)
            if n:
                phones.add(n)
        pj = person.profile_json or {}
        collected = pj.get("collected") if isinstance(pj.get("collected"), dict) else {}
        for k in ("phone_e164", "national_phone_number", "phone", "mobile_e164", "mobile_phone"):
            n = _norm_phone_e164(collected.get(k) if isinstance(collected.get(k), str) else None)
            if n:
                phones.add(n)
        for ph in phones:
            db.query(AuthMobileLoginOtpChallenge).filter(
                AuthMobileLoginOtpChallenge.phone_e164_normalized == ph
            ).delete(synchronize_session=False)
        report["auth_mobile_otp_phones_cleared"] = len(phones)

        for u in au:
            db.delete(u)
        report["admin_users_deleted"] = len(au)

        db.delete(person)
        db.commit()
        report["success"] = True
        return report
    except Exception:
        db.rollback()
        raise
