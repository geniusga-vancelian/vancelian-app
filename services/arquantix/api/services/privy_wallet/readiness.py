"""Diagnostics readiness Privy — infra prod et wallet client (sans exposer de secrets)."""
from __future__ import annotations

import os
import re
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.env import is_dev_mode
from database import Person, PersonExternalIdentity
from services.auth.person_identity_bridge import PROVIDER_PRIVY, get_pe_client_for_person
from services.privy_wallet.privy_api_client import privy_server_api_configured
from services.privy_wallet.repository import (
    PersonCryptoWalletRepository,
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
)
from services.privy_wallet.webhook_verifier import MODE_SVIX, _webhook_mode, _webhook_secret

_PROD_API_HOST = os.getenv("PRIVY_PROD_WEBHOOK_HOST", "api.arquantix.com").strip()


def _env_present(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def _jwt_exchange_ready() -> bool:
    mode = (os.getenv("PRIVY_EXCHANGE_VERIFICATION_MODE") or "stub").strip().lower()
    if mode == "stub":
        return is_dev_mode()
    if mode != "jwt":
        return False
    has_jwks = _env_present("PRIVY_JWKS_URL")
    has_pem = _env_present("PRIVY_JWT_VERIFICATION_KEY")
    return _env_present("PRIVY_APP_ID") and (has_jwks or has_pem)


def _webhook_ready() -> dict[str, Any]:
    mode = _webhook_mode()
    secret_ok = bool(_webhook_secret())
    stub_in_prod = mode == "stub" and not is_dev_mode()
    return {
        "verification_mode": mode,
        "secret_configured": secret_ok,
        "ready": secret_ok and mode == MODE_SVIX and not stub_in_prod,
        "blocking_reason": (
            None
            if secret_ok and mode == MODE_SVIX and not stub_in_prod
            else (
                "PRIVY_WEBHOOK_VERIFICATION_MODE=stub interdit hors dev"
                if stub_in_prod
                else "PRIVY_WEBHOOK_SECRET (ou SVIX_WEBHOOK_SECRET) manquant"
                if not secret_ok
                else f"Mode webhook inattendu: {mode}"
            )
        ),
        "expected_url": f"https://{_PROD_API_HOST}/api/webhooks/privy",
        "expected_event": "wallet.funds_deposited",
    }


def _ledger_schema_ready(db: Session) -> dict[str, Any]:
    tables = [
        "person_crypto_wallets",
        "person_wallet_deposits",
        "person_wallet_balances",
        "privy_webhook_events",
    ]
    present: dict[str, bool] = {}
    for table in tables:
        try:
            db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))  # noqa: S608
            present[table] = True
        except Exception:
            present[table] = False

    alembic_version: str | None = None
    try:
        row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
        alembic_version = row[0] if row else None
    except Exception:
        alembic_version = None

    migration_ok = (
        alembic_version is not None
        and str(alembic_version).isdigit()
        and int(alembic_version) >= 158
    )
    all_tables = all(present.values())

    return {
        "alembic_version": alembic_version,
        "migration_158_applied": migration_ok,
        "tables": present,
        "ready": migration_ok and all_tables,
        "blocking_reason": (
            None
            if migration_ok and all_tables
            else "Migration Alembic >= 158 requise (person_wallet_* + privy_webhook_events)"
        ),
    }


def get_privy_infra_readiness(db: Session) -> dict[str, Any]:
    """Checklist infra prod — aucune valeur secrète retournée."""
    schema = _ledger_schema_ready(db)
    webhook = _webhook_ready()
    exchange = {
        "mode": (os.getenv("PRIVY_EXCHANGE_VERIFICATION_MODE") or "stub").strip().lower(),
        "app_id_configured": _env_present("PRIVY_APP_ID"),
        "jwks_or_pem_configured": _env_present("PRIVY_JWKS_URL") or _env_present("PRIVY_JWT_VERIFICATION_KEY"),
        "ready": _jwt_exchange_ready(),
    }
    reconcile_api = {
        "app_secret_configured": _env_present("PRIVY_APP_SECRET"),
        "ready": privy_server_api_configured(),
    }

    blockers: list[str] = []
    if not schema["ready"] and schema.get("blocking_reason"):
        blockers.append(schema["blocking_reason"])
    if not webhook["ready"] and webhook.get("blocking_reason"):
        blockers.append(webhook["blocking_reason"])
    if not exchange["ready"]:
        blockers.append("JWT exchange Privy non prêt (mode jwt + APP_ID + JWKS/PEM)")
    if not reconcile_api["ready"]:
        blockers.append("PRIVY_APP_SECRET manquant — reconcile-wallets API indisponible")

    return {
        "ready_for_live_deposits": len(blockers) == 0,
        "blockers": blockers,
        "exchange": exchange,
        "webhook": webhook,
        "reconcile_api": reconcile_api,
        "ledger_schema": schema,
        "notes": [
            "Configurer le webhook dans le dashboard Privy vers expected_url.",
            "Ne pas utiliser le client mobile Flutter sur le portail web.",
        ],
    }


def get_customer_wallet_readiness(db: Session, person_id: UUID) -> dict[str, Any] | None:
    """Checklist wallet client — prêt à recevoir un dépôt live crédité en ledger."""
    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        return None

    pe = get_pe_client_for_person(db, person_id=person_id)
    identity = (
        db.query(PersonExternalIdentity)
        .filter(
            PersonExternalIdentity.person_id == person_id,
            PersonExternalIdentity.provider == PROVIDER_PRIVY,
        )
        .first()
    )

    wallets = PersonCryptoWalletRepository().list_active_for_person(db, person_id)
    primary = next((w for w in wallets if w.is_primary), wallets[0] if wallets else None)
    balances = PersonWalletBalanceRepository().list_for_person(db, person_id)
    deposits = PersonWalletDepositRepository().list_for_person(db, person_id, limit=5)

    checks: list[dict[str, Any]] = []

    def _check(key: str, ok: bool, detail: str, *, blocking: bool = True) -> None:
        checks.append({"key": key, "ok": ok, "detail": detail, "blocking": blocking})

    _check("person_exists", True, f"Person {person_id}")
    _check(
        "privy_identity_linked",
        identity is not None,
        identity.external_subject if identity else "Aucune ligne person_external_identities (provider=privy)",
    )
    _check(
        "active_wallet",
        len(wallets) > 0,
        f"{len(wallets)} wallet(s) actif(s)" if wallets else "Aucun person_crypto_wallets actif",
    )
    addr_ok = bool(primary and re.match(r"^0x[0-9a-fA-F]{40}$", primary.address or ""))
    _check(
        "primary_wallet_address",
        addr_ok,
        primary.address if primary else "Pas de wallet primaire",
    )
    _check(
        "pe_client_optional",
        pe is not None,
        f"pe_client_id={pe.id}" if pe else "Pas de pe_client (patrimoine partiel possible)",
        blocking=False,
    )
    _check(
        "reconcile_api_or_manual",
        privy_server_api_configured() or bool(primary),
        "API Privy ou adresse déjà persistée pour reconcile",
        blocking=False,
    )

    blockers = [c["detail"] for c in checks if c["blocking"] and not c["ok"]]
    infra = get_privy_infra_readiness(db)
    if not infra["ready_for_live_deposits"]:
        blockers.extend(infra["blockers"])

    return {
        "person_id": str(person_id),
        "email_hint": identity.external_email if identity else None,
        "privy_user_id": identity.external_subject if identity else None,
        "pe_client_id": str(pe.id) if pe else None,
        "primary_wallet": (
            {
                "id": str(primary.id),
                "address": primary.address,
                "chain_type": primary.chain_type,
                "chain_id": primary.chain_id,
            }
            if primary
            else None
        ),
        "balances_count": len(balances),
        "recent_deposits_count": len(deposits),
        "checks": checks,
        "infra": {
            "ready_for_live_deposits": infra["ready_for_live_deposits"],
            "blockers": infra["blockers"],
        },
        "ready_for_live_deposit": len(blockers) == 0,
        "blockers": blockers,
        "next_steps": _customer_next_steps(blockers, primary),
    }


def _customer_next_steps(blockers: list[str], primary: Any) -> list[str]:
    steps: list[str] = []
    if any("privy_identity" in b.lower() or "external_identities" in b.lower() for b in blockers):
        steps.append("Mobile/portail : login Privy OAuth ou OTP puis POST /auth/privy/link (JWT Vancelian).")
    if any("wallet" in b.lower() for b in blockers):
        steps.append("Créer le wallet embedded Privy puis POST /api/admin/privy-wallet/reconcile-wallets.")
    if any("WEBHOOK" in b or "Migration" in b or "jwt" in b.lower() for b in blockers):
        steps.append("Consolider infra prod (voir GET /api/admin/privy-wallet/infra-readiness).")
    if primary and not blockers:
        steps.append(
            f"Dépôt test : envoyer USDC, USDT, EURC ou ETH (Ethereum mainnet) vers {primary.address}."
        )
    return steps
