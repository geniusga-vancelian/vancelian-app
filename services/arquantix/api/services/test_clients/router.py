"""FastAPI routers for l’app mobile (/api/app/*)."""
import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from database import get_db

_logger = logging.getLogger(__name__)
from services.auth.device_attestation_dependencies import require_device_attestation_mobile
from services.portfolio_engine.clients.enums import ReferenceCurrency
from services.portfolio_engine.clients.models import Client as PeClient

from services.auth.privy_token_verifier import PrivyVerifyError, verify_privy_access_token

from .mobile_contact_email import (
    confirm_contact_email_change,
    request_contact_email_change,
)
from .schemas import (
    BootstrapResponse,
    BootstrapClientPayload,
    ContactEmailConfirmRequest,
    ContactEmailConfirmResponse,
    ContactEmailRequest,
    MobileAppProfileResponse,
    MobileSecurityPreferencesRead,
    SecurityPreferencesStructuredPatch,
    CashAccountPayload,
    CashResponse,
    CashTransactionPayload,
    CryptoPositionPayload,
    CryptoPositionsResponse,
    CryptoPositionsSummary,
    CryptoTransactionPayload,
    CryptoTransactionsResponse,
    CryptoWalletDetailPayload,
    CryptoWalletDetailResponse,
    EuroAccountPayload,
    EuroAccountResponse,
    EuroTransactionPayload,
    IbanDetailsPayload,
    IbanDetailsResponse,
    PortfolioBreakdownResponse,
    TransactionDetailResponse,
)
from .mobile_profile import (
    build_mobile_profile_dict,
    build_initials,
    load_person_for_client,
    sync_pe_client_email_from_collected,
)
from .security_preferences_v1 import (
    build_security_preferences_read_dict,
    merge_patch_into_security,
    security_blob_from_person,
)
from .mobile_identity import mobile_app_client, mobile_bearer, resolve_bootstrap_client
from .service import TestClientService
from services.exchange.service import (
    ExchangeService as _ExchangeService,
    ExchangeError as _ExchangeError,
)
from services.exchange.error_mapper import raise_exchange_error as _raise_exchange_error
from services.portfolio_engine.provisioning.errors import ClientNotEligibleError as _ClientNotEligibleError
from services.exchange.schemas import (
    ExchangeBuyRequest as _ExchangeBuyRequest,
    ExchangeSellRequest as _ExchangeSellRequest,
    SwapPreviewRequest as _SwapPreviewRequest,
    SwapRequest as _SwapRequest,
)
from services.wallet_history.service import build_wallet_history
from services.wallet_statistics.service import build_wallet_statistics


def _simulate_trade_latency() -> None:
    """Random delay (0.5–2s) to simulate realistic trade execution time."""
    import time
    import random
    time.sleep(random.uniform(0.5, 2.0))


# ---------------------------------------------------------------------------
# Bootstrap router — /api/app
# ---------------------------------------------------------------------------
_svc = TestClientService()

bootstrap_router = APIRouter(prefix="/api/app", tags=["app-bootstrap"])

mobile_flutter_router = APIRouter(prefix="/api/mobile/flutter", tags=["app-mobile-flutter"])


def _get_mobile_profile_response(
    db: Session,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> MobileAppProfileResponse:
    client = resolve_bootstrap_client(db, credentials)
    return MobileAppProfileResponse.model_validate(build_mobile_profile_dict(db, client))


def _bootstrap_client_payload(db: Session, client: PeClient) -> BootstrapClientPayload:
    client = sync_pe_client_email_from_collected(db, client)
    base = BootstrapClientPayload.model_validate(client)
    person = load_person_for_client(db, client)
    initials = build_initials(client_email=base.email, person=person)
    return base.model_copy(update={"initials": initials})


@bootstrap_router.get("/bootstrap", response_model=BootstrapResponse)
def get_bootstrap(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    client = resolve_bootstrap_client(db, credentials)
    return BootstrapResponse(client=_bootstrap_client_payload(db, client))


@bootstrap_router.get("/profile", response_model=MobileAppProfileResponse)
def get_app_profile(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    return _get_mobile_profile_response(db, credentials)


@mobile_flutter_router.get("/profile", response_model=MobileAppProfileResponse)
def get_app_profile_mobile_flutter_alias(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    """Alias pour le client Flutter ([Config.mobileAppProfileUrl]). Identique à GET /api/app/profile."""
    return _get_mobile_profile_response(db, credentials)


@mobile_flutter_router.patch(
    "/profile/security-preferences",
    response_model=MobileSecurityPreferencesRead,
    summary="Préférences sécurité / notifications (profile_json.security, modèle V1 structuré)",
)
def patch_security_preferences_mobile_flutter(
    payload: SecurityPreferencesStructuredPatch,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
    _pr_e: None = Depends(require_device_attestation_mobile()),
):
    """PATCH structuré uniquement ; champs legacy plats sont dérivés côté serveur (pas d’écriture legacy)."""
    person = load_person_for_client(db, client)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person profile not found for this client.",
        )
    pj: dict[str, Any] = dict(person.profile_json or {})
    sec = security_blob_from_person(person.profile_json)

    bio_patch = (
        payload.biometric.model_dump(exclude_unset=True, mode="json")
        if payload.biometric
        else None
    )
    push_patch = (
        payload.push_notifications.model_dump(exclude_unset=True, mode="json")
        if payload.push_notifications
        else None
    )
    try:
        new_sec = merge_patch_into_security(sec, bio_patch, push_patch)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    pj["security"] = new_sec
    person.profile_json = pj
    flag_modified(person, "profile_json")
    db.add(person)
    db.commit()
    db.refresh(person)
    return MobileSecurityPreferencesRead.model_validate(
        build_security_preferences_read_dict(security_blob_from_person(person.profile_json))
    )


@mobile_flutter_router.post(
    "/profile/contact-email/request",
    response_model=MobileAppProfileResponse,
    summary="Demander un changement d’e-mail (statut pending, OTP Privy requis)",
)
def post_contact_email_change_request(
    payload: ContactEmailRequest,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
    _pr_e: None = Depends(require_device_attestation_mobile()),
):
    person = load_person_for_client(db, client)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person profile not found for this client.",
        )
    try:
        request_contact_email_change(person, payload.email)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    db.add(person)
    db.commit()
    db.refresh(person)
    return MobileAppProfileResponse.model_validate(build_mobile_profile_dict(db, client))


@mobile_flutter_router.post(
    "/profile/contact-email/confirm",
    response_model=ContactEmailConfirmResponse,
    summary="Confirmer le changement d’e-mail après OTP Privy (statut confirmed en base)",
)
def post_contact_email_change_confirm(
    payload: ContactEmailConfirmRequest,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
    _pr_e: None = Depends(require_device_attestation_mobile()),
):
    person = load_person_for_client(db, client)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person profile not found for this client.",
        )
    try:
        verified = verify_privy_access_token(payload.privy_access_token)
    except PrivyVerifyError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    from database import PersonExternalIdentity
    from services.auth.person_identity_bridge import PROVIDER_PRIVY

    privy_link = (
        db.query(PersonExternalIdentity)
        .filter(
            PersonExternalIdentity.person_id == person.id,
            PersonExternalIdentity.provider == PROVIDER_PRIVY,
        )
        .first()
    )
    if (
        privy_link is not None
        and privy_link.external_subject != verified.privy_user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "contact_email.privy_mismatch",
                "message": "Le jeton Privy ne correspond pas à l’identité liée au compte.",
            },
        )

    try:
        result = confirm_contact_email_change(
            db,
            person=person,
            client=client,
            new_email=payload.email,
            verified_privy_email=verified.email,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    db.commit()
    db.refresh(person)
    return ContactEmailConfirmResponse.model_validate(result)


class ReferenceCurrencyUpdate(BaseModel):
    reference_currency: ReferenceCurrency

    @field_validator("reference_currency", mode="before")
    @classmethod
    def normalise_upper(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper()
        return v


class ReferenceCurrencyResponse(BaseModel):
    reference_currency: str


@bootstrap_router.patch("/profile/reference-currency", response_model=ReferenceCurrencyResponse)
def update_reference_currency(
    payload: ReferenceCurrencyUpdate,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    client.reference_currency = payload.reference_currency.value
    db.commit()
    db.refresh(client)
    return ReferenceCurrencyResponse(reference_currency=client.reference_currency)


@bootstrap_router.get("/cash", response_model=CashResponse)
def get_cash(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    data = _svc.get_cash_data(db, client=client)
    client_payload = _bootstrap_client_payload(db, data["client"])

    cash_account = None
    if data["cash_account"]:
        cash_account = CashAccountPayload(**data["cash_account"])

    transactions = [CashTransactionPayload(**t) for t in data["recent_transactions"]]

    return CashResponse(
        client=client_payload,
        cash_account=cash_account,
        recent_transactions=transactions,
        last_updated=data.get("last_updated"),
    )


@bootstrap_router.get("/euro-account", response_model=EuroAccountResponse)
def get_euro_account(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    data = _svc.get_euro_account_data(db, client=client)
    client_payload = _bootstrap_client_payload(db, data["client"])

    account = None
    if data["account"]:
        account = EuroAccountPayload(**data["account"])

    transactions = [EuroTransactionPayload(**t) for t in data["transactions"]]

    return EuroAccountResponse(
        client=client_payload,
        account=account,
        transactions=transactions,
    )


@bootstrap_router.get("/euro-account/statement.pdf")
def get_euro_account_statement_pdf(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Relevé IBAN PDF généré à la volée (pas de persistance)."""
    from pdf.iban_statement_mapper import payload_to_template_context
    from pdf.iban_statement_renderer import render_iban_statement_pdf

    from .iban_statement_payload import build_iban_statement_payload_for_client

    # Diagnostic unifié : payload → mapper → renderer (logs par étape).
    _logger.info("iban_statement_pdf: building payload")
    try:
        payload = build_iban_statement_payload_for_client(db, client)
    except Exception:
        _logger.exception("iban_statement_pdf: failure during payload build")
        raise

    if payload is None:
        _logger.info(
            "iban_statement_pdf: no EUR custody account for client client_id=%s",
            client.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No EUR custody account for this client.",
        )

    _logger.info("iban_statement_pdf: mapping payload to template context")
    try:
        ctx = payload_to_template_context(payload)
    except Exception:
        _logger.exception("iban_statement_pdf: failure during context mapping")
        raise

    _logger.info("iban_statement_pdf: rendering pdf")
    try:
        pdf_bytes = render_iban_statement_pdf(ctx)
    except FileNotFoundError as exc:
        _logger.exception("iban_statement_pdf: fichier ressource PDF manquant (template/CSS)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ressource de rendu PDF manquante sur le serveur.",
        ) from exc
    except (OSError, ImportError) as exc:
        # WeasyPrint : import CFFI/cairo, dlopen libs, ou autre OSError en phase rendu.
        if isinstance(exc, OSError):
            _logger.error(
                "iban_statement_pdf: OSError errno=%s (ENOENT=2 fichier; None=souvent dlopen libs)",
                getattr(exc, "errno", None),
            )
        _logger.exception(
            "iban_statement_pdf: moteur WeasyPrint indisponible ou libs système manquantes",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Génération PDF indisponible : le serveur n'a pas les bibliothèques "
                "nécessaires (WeasyPrint). En local : installer Pango/Cairo ou lancer l'API via Docker."
            ),
        ) from exc
    except Exception as exc:
        _logger.exception("iban_statement_pdf: failure during pdf rendering")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération du relevé.",
        ) from exc

    _logger.info("iban_statement_pdf: success pdf_bytes=%s", len(pdf_bytes))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="releve-euro.pdf"'},
    )


@bootstrap_router.get("/iban-details", response_model=IbanDetailsResponse)
def get_iban_details(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    data = _svc.get_iban_details(db, client=client)
    client_payload = _bootstrap_client_payload(db, data["client"])

    iban_details = None
    if data["iban_details"]:
        iban_details = IbanDetailsPayload(**data["iban_details"])

    return IbanDetailsResponse(
        client=client_payload,
        iban_details=iban_details,
    )


@bootstrap_router.get("/crypto-positions", response_model=CryptoPositionsResponse)
def get_crypto_positions(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    data = _svc.get_crypto_positions(db, client=client)
    client_payload = _bootstrap_client_payload(db, data["client"])
    summary = CryptoPositionsSummary(**data["summary"])
    positions = [CryptoPositionPayload(**p) for p in data["positions"]]
    return CryptoPositionsResponse(
        client=client_payload,
        summary=summary,
        positions=positions,
    )


@bootstrap_router.get("/portfolio/breakdown", response_model=PortfolioBreakdownResponse)
def get_portfolio_breakdown(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Breakdown patrimoine par actif — scopes PE (lecture seule, non additif)."""
    from services.portfolio_engine.portfolio_breakdown import build_portfolio_breakdown

    person_id = getattr(client, "person_id", None)
    if person_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client sans person_id — breakdown indisponible",
        )
    payload = build_portfolio_breakdown(db, person_id)
    return PortfolioBreakdownResponse(**payload)


@bootstrap_router.get("/crypto-positions/direct")
def get_direct_crypto_positions(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Return only the direct (non-bundle) holdings, sourced from the direct portfolio overlay.

    Falls back to crypto_positions minus bundle atoms if the direct portfolio
    has not been backfilled yet (auto-triggers a backfill in that case).
    """
    from decimal import Decimal as D, ROUND_HALF_UP

    from database import MarketDataBar1d, MarketDataInstrument, MarketDataLatestQuote
    from services.exchange.assets import ASSET_PRECISION, ASSET_PROVIDER_SYMBOL_MAP
    from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
    from services.portfolio_engine.direct_overlay import (
        ensure_direct_portfolio,
        backfill_direct_atoms,
        _normalize_asset_symbol,
    )
    from services.portfolio_engine.vault_execution.vault_funding import (
        resolve_trading_available_by_asset,
    )
    from services.portfolio_engine.positions.models import PositionAtom
    from services.portfolio_engine.instruments.models import Instrument
    from services.portfolio_engine.assets.models import Asset
    from .schemas import ASSET_NAMES

    direct_pf = ensure_direct_portfolio(db, client.id)

    atoms = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.position_type == "spot",
            PositionAtom.status == "open",
        )
        .all()
    )

    if not atoms:
        backfill_direct_atoms(db, client.id)
        db.commit()
        atoms = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == direct_pf.id,
                PositionAtom.position_type == "spot",
                PositionAtom.status == "open",
            )
            .all()
        )

    eurusdt_rate = get_eurusdt_rate(db, strict=False)

    # Build a map of lending-reserved amounts per asset from crypto_positions
    # so we can subtract committed funds from the displayed direct balance.
    from services.exchange.repository import CryptoPositionRepository
    all_crypto_pos = CryptoPositionRepository.list_by_client(db, client.id)
    lending_reserved: dict[str, D] = {}
    for cp in all_crypto_pos:
        total_bal = D(str(cp.balance))
        avail_bal = D(str(cp.available_balance))
        reserved = total_bal - avail_bal
        if reserved > 0:
            lending_reserved[cp.asset.upper()] = reserved

    enriched = []
    total_value_eur = D("0")
    total_value_usd = D("0")

    for atom in atoms:
        qty = D(str(atom.quantity or 0))
        if qty <= 0:
            continue

        instrument = atom.instrument or (
            db.query(Instrument).filter(Instrument.id == atom.instrument_id).first()
        )
        if not instrument:
            continue
        asset_obj = db.query(Asset).filter(Asset.id == instrument.asset_id).first()
        if not asset_obj:
            continue
        asset_symbol = _normalize_asset_symbol(asset_obj.symbol.upper())

        # Subtract lending-reserved amount to avoid double-counting with Placements
        reserved = lending_reserved.get(asset_symbol, D("0"))
        display_qty = qty - reserved
        if display_qty <= 0:
            continue

        precision = ASSET_PRECISION.get(asset_symbol, 8)
        balance_str = f"{display_qty:.{precision}f}"

        price_eur = None
        estimated_value_eur = None
        price_usd = None
        estimated_value_usd = None
        perf_1d_pct = None

        provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(asset_symbol)
        if provider_symbol:
            inst = (
                db.query(MarketDataInstrument)
                .filter(MarketDataInstrument.provider_symbol == provider_symbol)
                .first()
            )
            if inst:
                quote = (
                    db.query(MarketDataLatestQuote)
                    .filter(MarketDataLatestQuote.instrument_id == inst.id)
                    .first()
                )
                if quote and quote.last_price is not None:
                    p_usdt = D(str(quote.last_price))
                    p_eur = usdt_to_eur(p_usdt, eurusdt_rate)
                    price_eur = f"{p_eur:.2f}"
                    val_eur = (display_qty * p_eur).quantize(D("0.01"))
                    estimated_value_eur = f"{val_eur:.2f}"
                    total_value_eur += val_eur

                    price_usd = f"{p_usdt:.2f}"
                    val_usd = (display_qty * p_usdt).quantize(D("0.01"))
                    estimated_value_usd = f"{val_usd:.2f}"
                    total_value_usd += val_usd

                prev_bar = (
                    db.query(MarketDataBar1d)
                    .filter(MarketDataBar1d.instrument_id == inst.id)
                    .order_by(MarketDataBar1d.open_time.desc())
                    .offset(1).limit(1)
                    .first()
                )
                if prev_bar and prev_bar.close and quote and quote.last_price:
                    prev_close = D(str(prev_bar.close))
                    if prev_close > 0:
                        pct = ((D(str(quote.last_price)) - prev_close) / prev_close * 100).quantize(D("0.01"), rounding=ROUND_HALF_UP)
                        perf_1d_pct = f"{pct:+.2f}"

        cost_basis = D(str(atom.cost_basis or 0))
        avg_entry = D(str(atom.average_entry_price or 0))
        trading_available = resolve_trading_available_by_asset(
            db,
            client_id=client.id,
            asset=asset_symbol,
        )
        trading_available_str = f"{trading_available:.{precision}f}"

        enriched.append({
            "asset": asset_symbol,
            "name": ASSET_NAMES.get(asset_symbol, asset_symbol),
            "balance": balance_str,
            "available_balance": balance_str,
            "trading_available": trading_available_str,
            "price_eur": price_eur,
            "estimated_value_eur": estimated_value_eur,
            "price_usd": price_usd,
            "estimated_value_usd": estimated_value_usd,
            "performance_1d_pct": perf_1d_pct,
            "icon_key": asset_symbol.lower(),
            "cost_basis": f"{cost_basis:.2f}" if cost_basis > 0 else None,
            "average_entry_price": f"{avg_entry:.2f}" if avg_entry > 0 else None,
        })

    enriched.sort(
        key=lambda x: D(x["estimated_value_eur"]) if x["estimated_value_eur"] else D("0"),
        reverse=True,
    )

    from services.privy_wallet.patrimony_merge import merge_app_crypto_positions

    person_id = getattr(client, "person_id", None)
    merged = merge_app_crypto_positions(enriched, db, person_id=person_id)

    if person_id is not None:
        from services.portfolio_engine.portfolio_breakdown import build_portfolio_breakdown

        breakdown = build_portfolio_breakdown(db, person_id)
        swappable_map = breakdown.get("swappable_by_asset") or {}
        on_chain_map = {
            str(row.get("symbol") or "").upper(): row.get("on_chain_balance_base")
            for row in (breakdown.get("assets") or [])
        }
        for row in merged:
            asset = str(row.get("asset") or "").upper()
            if asset in swappable_map:
                row["swappable_balance"] = swappable_map[asset]
            if asset in on_chain_map and on_chain_map[asset] is not None:
                row["on_chain_balance_base"] = on_chain_map[asset]

    total_value_eur = D("0")
    total_value_usd = D("0")
    for entry in merged:
        if entry.get("estimated_value_eur"):
            total_value_eur += D(str(entry["estimated_value_eur"]))
        if entry.get("estimated_value_usd"):
            total_value_usd += D(str(entry["estimated_value_usd"]))

    return {
        "client": {"id": str(client.id), "name": getattr(client, "name", ""), "email": getattr(client, "email", "")},
        "summary": {
            "total_value_eur": f"{total_value_eur:.2f}",
            "total_value_usd": f"{total_value_usd:.2f}",
            "positions_count": len(merged),
            "scope": "direct",
        },
        "positions": merged,
    }


@bootstrap_router.get("/crypto-positions/{asset}", response_model=CryptoWalletDetailResponse)
def get_crypto_wallet_detail(
    asset: str,
    portal_chain: Optional[str] = Query(
        None,
        description="Écosystème portail (base, ethereum, solana) — filtre le solde Privy par chain_id.",
    ),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    chain_id = None
    if portal_chain:
        chain_id = {"base": 8453, "ethereum": 1, "solana": 0}.get(portal_chain.strip().lower())
    data = _svc.get_crypto_wallet_detail(db, asset, client=client, chain_id=chain_id)
    client_payload = _bootstrap_client_payload(db, data["client"])
    detail = CryptoWalletDetailPayload(**data["detail"]) if data["detail"] else None
    return CryptoWalletDetailResponse(client=client_payload, detail=detail)


@bootstrap_router.get("/crypto-positions/{asset}/transactions", response_model=CryptoTransactionsResponse)
def get_crypto_transactions(
    asset: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    data = _svc.get_crypto_transactions(db, asset, client=client)
    client_payload = _bootstrap_client_payload(db, data["client"])
    txs = [CryptoTransactionPayload(**t) for t in data["transactions"]]
    return CryptoTransactionsResponse(client=client_payload, asset=data["asset"], transactions=txs)


@bootstrap_router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionDetailResponse,
)
def get_transaction_detail(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    data = _svc.get_transaction_detail(db, transaction_id, client=client)

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return TransactionDetailResponse(**data)


@bootstrap_router.get("/transactions/{transaction_id}/operation-statement.pdf")
def get_transaction_operation_statement_pdf(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """PDF relevé d’une seule opération (custody ou Exchange) — pipeline ``operation_statement_*``."""
    from pdf.operation_statement_mapper import operation_statement_payload_to_template_context
    from pdf.operation_statement_renderer import render_operation_statement_pdf

    from .custody_operation_statement import build_custody_operation_statement_payload
    from .exchange_operation_statement import build_exchange_operation_statement_payload
    from .operation_resolver import OperationResolver
    from .operation_statement_errors import OperationStatementHttpError
    from .operation_statement_snapshot_service import (
        create_snapshot,
        get_snapshot,
        payload_from_snapshot_row,
    )

    _logger.info(
        "OPERATION_STATEMENT_PDF: entry transaction_id=%s client_id=%s",
        transaction_id,
        client.id,
    )

    ref = OperationResolver.resolve(db, client, transaction_id)
    if ref is None:
        _logger.info(
            "OPERATION_STATEMENT_PDF: resolve miss transaction_id=%s client_id=%s",
            transaction_id,
            client.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relevé indisponible : transaction introuvable ou non associée à votre compte.",
            headers={"X-Vancelian-Error-Code": "operation_statement_not_found"},
        )

    _logger.info(
        "OPERATION_STATEMENT_PDF: resolved source_system=%s source_id=%s",
        ref.source_system,
        ref.source_id,
    )

    snap_row = get_snapshot(db, client.id, ref)
    if snap_row is not None:
        _logger.info(
            "OPERATION_STATEMENT_PDF: snapshot hit schema_version=%s content_sha256=%s…",
            snap_row.schema_version,
            (snap_row.content_sha256 or "")[:16],
        )
        loaded_from_snapshot = True
        try:
            payload = payload_from_snapshot_row(snap_row)
        except Exception:
            _logger.exception("OPERATION_STATEMENT_PDF: failed to load snapshot payload")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Relevé indisponible : données de snapshot invalides.",
            ) from None
    else:
        _logger.info("OPERATION_STATEMENT_PDF: snapshot miss — building from adapters")
        loaded_from_snapshot = False
        try:
            if ref.source_system == "custody":
                payload = build_custody_operation_statement_payload(
                    db, client, transaction_id, resolved_ref=ref
                )
            else:
                payload = build_exchange_operation_statement_payload(
                    db, client, transaction_id, resolved_ref=ref
                )
        except OperationStatementHttpError as exc:
            _logger.info(
                "operation_statement_pdf: rejected code=%s transaction_id=%s client_id=%s",
                exc.code,
                transaction_id,
                client.id,
            )
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.message,
                headers={"X-Vancelian-Error-Code": exc.code},
            ) from exc
        except Exception:
            _logger.exception("OPERATION_STATEMENT_PDF: failure during payload build")
            raise

    _logger.info(
        "OPERATION_STATEMENT_PDF: payload_source=%s",
        "snapshot" if loaded_from_snapshot else "adapters",
    )

    try:
        ctx = operation_statement_payload_to_template_context(payload)
    except Exception:
        _logger.exception("OPERATION_STATEMENT_PDF: failure during context mapping")
        raise

    try:
        pdf_bytes = render_operation_statement_pdf(ctx)
    except FileNotFoundError as exc:
        _logger.exception("OPERATION_STATEMENT_PDF: missing template/css")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ressource de rendu PDF manquante sur le serveur.",
        ) from exc
    except (OSError, ImportError) as exc:
        if isinstance(exc, OSError):
            _logger.error(
                "operation_statement_pdf: OSError errno=%s",
                getattr(exc, "errno", None),
            )
        _logger.exception("OPERATION_STATEMENT_PDF: weasyprint unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Génération PDF indisponible : le serveur n'a pas les bibliothèques "
                "nécessaires (WeasyPrint). En local : installer Pango/Cairo ou lancer l'API via Docker."
            ),
        ) from exc
    except Exception:
        _logger.exception("OPERATION_STATEMENT_PDF: failure during pdf rendering")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération du relevé.",
        )

    if not loaded_from_snapshot:
        try:
            create_snapshot(db, client.id, ref, payload)
            db.commit()
        except Exception:
            _logger.exception("OPERATION_STATEMENT_PDF: failed to persist snapshot")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de l’enregistrement du relevé documentaire.",
            ) from None

    fname = f'releve-operation-{transaction_id}.pdf'
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@bootstrap_router.get("/wallet/history")
def get_wallet_history(
    period: str = Query("ALL", pattern="^(1D|1W|1M|ALL)$"),
    asset: Optional[str] = Query(None, description="Filter history to a single asset (e.g. BTC)"),
    mode: str = Query("value", pattern="^(value|performance_value|performance_pct)$"),
    scope: Optional[str] = Query(None, pattern="^(crypto)$", description="Scope for global series (e.g. crypto)"),
    portfolio_scope: Optional[str] = Query(None, pattern="^(direct|bundle|global)$"),
    portfolio_id: Optional[str] = Query(None, description="Portfolio UUID (required when portfolio_scope=bundle)"),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Historical wallet chart data.

    *mode* controls the metric returned:
      - ``value``: NAV (default)
      - ``performance_value``: cumulative realized + unrealized PnL in ref currency
      - ``performance_pct``: reserved for future use

    *portfolio_scope* narrows orders to a portfolio overlay:
      - ``direct`` → non-bundle orders only
      - ``bundle`` → bundle orders for *portfolio_id* only
      - ``global`` / omitted → all orders (backward compatible)
    """
    ref_currency = getattr(client, "reference_currency", "EUR") or "EUR"
    result = build_wallet_history(
        db, client.id, reference_currency=ref_currency,
        asset=asset.upper() if asset else None,
        mode=mode,
        portfolio_scope=portfolio_scope,
        portfolio_id=portfolio_id,
    )

    if period != "ALL" and result["points"]:
        from datetime import datetime, timedelta, timezone as tz

        now = datetime.now(tz.utc)
        delta_map = {"1D": timedelta(days=1), "1W": timedelta(weeks=1), "1M": timedelta(days=30)}
        cutoff = now - delta_map[period]
        result["points"] = [
            p for p in result["points"]
            if datetime.fromisoformat(p["timestamp"]) >= cutoff
        ]

    return result


@bootstrap_router.get("/wallet/statistics/{asset}")
def get_wallet_statistics(
    asset: str,
    portfolio_scope: Optional[str] = Query(None, pattern="^(direct|bundle|global)$"),
    portfolio_id: Optional[str] = Query(None, description="Portfolio UUID (required when portfolio_scope=bundle)"),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Per-asset wallet statistics (performance, trading activity, risk).

    *portfolio_scope* narrows to a specific portfolio overlay:
      - ``direct`` → non-bundle stats
      - ``bundle`` → bundle stats for *portfolio_id*
      - ``global`` / omitted → all (backward compatible)
    """
    ref_currency = getattr(client, "reference_currency", "EUR") or "EUR"
    return build_wallet_statistics(
        db, client.id, asset.upper(), reference_currency=ref_currency,
        portfolio_scope=portfolio_scope, portfolio_id=portfolio_id,
    )


@bootstrap_router.get("/portfolio/statistics")
def get_portfolio_statistics(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Consolidated crypto portfolio statistics: direct + bundles."""
    from decimal import Decimal as D, ROUND_HALF_UP as RHU

    from services.exchange.repository import CryptoPositionRepository
    from services.portfolio_engine.portfolios.models import Portfolio
    from services.portfolio_engine.positions.models import PositionAtom
    from services.portfolio_engine.instruments.models import Instrument
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.instruments.price_bridge import get_instrument_price
    from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
    from services.exchange.models import ExchangeOrder

    ref_currency = getattr(client, "reference_currency", "EUR") or "EUR"
    eurusdt_rate = get_eurusdt_rate(db, strict=False)

    # ── Consolidated positions (crypto_positions) ──────────────────
    positions = CryptoPositionRepository.list_by_client(db, client.id)
    total_value = D("0")
    total_invested = D("0")
    total_realized = D("0")
    total_unrealized = D("0")

    per_asset: dict[str, dict] = {}
    for pos in positions:
        balance = D(str(pos.balance))
        s = build_wallet_statistics(db, client.id, pos.asset, reference_currency=ref_currency)
        if s.get("trade_count", 0) == 0 and balance <= 0:
            continue
        cv = D(str(s["current_value"]))
        rp = D(str(s["realized_pnl"]))
        up = D(str(s["unrealized_pnl"]))
        aep = D(str(s["average_entry_price"]))
        tb = D(str(s.get("total_bought", 0)))
        abp = D(str(s.get("avg_buy_price", 0)))
        cost = tb * abp if tb > 0 else balance * aep
        tp = rp + up

        total_value += cv
        total_invested += cost
        total_realized += rp
        total_unrealized += up

        per_asset[pos.asset] = {
            "asset": pos.asset,
            "current_value": float(cv.quantize(D("0.01"), rounding=RHU)),
            "pnl": float(tp.quantize(D("0.01"), rounding=RHU)),
            "weight": 0.0,
        }

    total_pnl = total_realized + total_unrealized
    roi_pct = float((total_pnl / total_invested * 100).quantize(D("0.01"), rounding=RHU)) if total_invested > 0 else 0.0

    for a in per_asset.values():
        if total_value > 0:
            a["weight"] = float((D(str(a["current_value"])) / total_value * 100).quantize(D("0.01"), rounding=RHU))

    allocation = sorted(per_asset.values(), key=lambda x: x["current_value"], reverse=True)

    # ── Contributions ─────────────────────────────────────────────
    contributions = []
    for a in allocation:
        pnl = a["pnl"]
        contrib = (pnl / float(total_pnl) * 100) if total_pnl != 0 else 0.0
        contributions.append({
            "asset": a["asset"],
            "pnl": round(pnl, 2),
            "contribution_pct": round(contrib, 2),
        })

    # ── Source breakdown: direct vs bundles vs cash ────────────────
    direct_portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.client_id == client.id,
            Portfolio.portfolio_type == "direct_portfolio",
            Portfolio.status == "active",
        )
        .first()
    )
    bundle_portfolios = (
        db.query(Portfolio)
        .filter(
            Portfolio.client_id == client.id,
            Portfolio.portfolio_type == "bundle_portfolio",
            Portfolio.status == "active",
        )
        .all()
    )

    def _sum_portfolio_value(portfolio_id) -> tuple[float, float]:
        atoms = (
            db.query(PositionAtom)
            .filter(PositionAtom.portfolio_id == portfolio_id, PositionAtom.status == "open")
            .all()
        )
        spot_val = D("0")
        cash_val = D("0")
        for atom in atoms:
            qty = D(str(atom.quantity or 0))
            if qty <= 0:
                continue
            try:
                pi = get_instrument_price(db, atom.instrument_id)
                p_usdt = D(pi["price"]) if pi.get("price") else None
                if p_usdt is not None:
                    p_eur = usdt_to_eur(p_usdt, eurusdt_rate)
                    mv = (qty * p_eur).quantize(D("0.01"), rounding=RHU)
                    if atom.position_type == "cash":
                        cash_val += mv
                    else:
                        spot_val += mv
            except Exception:
                pass
        return float(spot_val), float(cash_val)

    direct_value = 0.0
    if direct_portfolio:
        dv, _ = _sum_portfolio_value(direct_portfolio.id)
        direct_value = dv

    bundle_spot_total = 0.0
    bundle_cash_total = 0.0
    for bp in bundle_portfolios:
        sv, cv_ = _sum_portfolio_value(bp.id)
        bundle_spot_total += sv
        bundle_cash_total += cv_

    source_total = direct_value + bundle_spot_total + bundle_cash_total
    source_breakdown = {
        "direct_value": round(direct_value, 2),
        "direct_pct": round(direct_value / source_total * 100, 2) if source_total > 0 else 0.0,
        "bundle_value": round(bundle_spot_total, 2),
        "bundle_pct": round(bundle_spot_total / source_total * 100, 2) if source_total > 0 else 0.0,
        "bundle_cash_value": round(bundle_cash_total, 2),
        "bundle_cash_pct": round(bundle_cash_total / source_total * 100, 2) if source_total > 0 else 0.0,
    }

    # ── Deployment ────────────────────────────────────────────────
    invested_value = float(total_value) - bundle_cash_total
    invested_pct = (invested_value / float(total_value) * 100) if total_value > 0 else 0.0
    cash_pct = (bundle_cash_total / float(total_value) * 100) if total_value > 0 else 0.0

    direct_wallet_count = len([a for a in per_asset.values() if a["current_value"] > 0])
    active_bundles_count = len(bundle_portfolios)

    deployment = {
        "invested_pct": round(invested_pct, 2),
        "cash_pct": round(cash_pct, 2),
        "cash_value": round(bundle_cash_total, 2),
        "direct_wallets": direct_wallet_count,
        "active_bundles": active_bundles_count,
    }

    # ── Activity ──────────────────────────────────────────────────
    all_orders = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client.id,
            ExchangeOrder.status == "completed",
        )
        .all()
    )
    direct_trades = 0
    bundle_invest_events = 0
    rebalance_events = 0
    last_activity = None
    for o in all_orders:
        md = o.metadata_ or {}
        scope = md.get("portfolio_scope", "direct")
        action = md.get("bundle_action")
        if scope == "direct":
            direct_trades += 1
        elif scope == "bundle":
            if action == "rebalance":
                rebalance_events += 1
            else:
                bundle_invest_events += 1
        ts = o.created_at
        if ts and (last_activity is None or ts > last_activity):
            last_activity = ts

    activity = {
        "direct_trades": direct_trades,
        "bundle_invest_events": bundle_invest_events,
        "rebalance_events": rebalance_events,
        "last_activity": last_activity.isoformat() if last_activity else None,
    }

    # ── Risk ──────────────────────────────────────────────────────
    max_weight_asset = allocation[0]["asset"] if allocation else None
    max_weight_pct = allocation[0]["weight"] if allocation else 0.0

    risk = {
        "assets_count": len(per_asset),
        "concentration_asset": max_weight_asset,
        "concentration_pct": round(max_weight_pct, 2),
        "volatility_30d": None,
        "max_drawdown": None,
    }

    return {
        "currency": ref_currency,
        "performance": {
            "current_value": float(total_value.quantize(D("0.01"), rounding=RHU)),
            "total_invested": float(total_invested.quantize(D("0.01"), rounding=RHU)),
            "total_pnl": float(total_pnl.quantize(D("0.01"), rounding=RHU)),
            "performance_pct": roi_pct,
            "realized_pnl": float(total_realized.quantize(D("0.01"), rounding=RHU)),
            "unrealized_pnl": float(total_unrealized.quantize(D("0.01"), rounding=RHU)),
        },
        "allocation": allocation,
        "contributions": contributions,
        "source_breakdown": source_breakdown,
        "deployment": deployment,
        "activity": activity,
        "risk": risk,
    }


# ---------------------------------------------------------------------------
# Global account statistics (fiat + crypto + bundles)
# ---------------------------------------------------------------------------

@bootstrap_router.get("/portfolio/global/statistics")
def get_global_portfolio_statistics(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Wealth-management-level statistics: fiat + direct crypto + bundles.

    Uses centralized valuation.py so numbers match every other page.
    """
    from decimal import Decimal as D, ROUND_HALF_UP as RHU

    from services.exchange.repository import CryptoPositionRepository
    from services.exchange.models import ExchangeOrder
    from sqlalchemy import func, or_ as _or
    from services.custody.models import CustodyAccount as _CA, CustodyTransaction as _CT
    from services.custody.enums import TransactionDirection as _TD, TransactionKind as _TK, TransactionType as _TT
    from services.portfolio_engine.valuation import (
        get_portfolio_breakdown,
        get_net_deposits as _get_net_deposits,
        get_pnl as _get_pnl,
        get_fx_rate as _get_fx_rate,
    )

    ref_currency = getattr(client, "reference_currency", "EUR") or "EUR"

    breakdown_data = get_portfolio_breakdown(db, client.id)

    from services.privy_wallet.patrimony_merge import merge_app_crypto_positions, privy_nav_eur

    # get_portfolio_breakdown returns EUR; convert to ref_currency if needed
    eurusdt_rate = _get_fx_rate(db)
    _to_ref = (lambda v: round(v * float(eurusdt_rate), 2)) if ref_currency != "EUR" else (lambda v: v)

    privy_eur = float(privy_nav_eur(db, getattr(client, "person_id", None)))
    tv_f = _to_ref(breakdown_data["total_value"]) + _to_ref(privy_eur)
    fiat_balance = _to_ref(breakdown_data["fiat"])
    direct_crypto_f = _to_ref(breakdown_data["crypto_direct"])
    bundle_total_f = _to_ref(breakdown_data["bundles"])

    net_deposits = _to_ref(float(_get_net_deposits(db, client.id)))
    pnl_data = _get_pnl(db, client.id)
    total_realized = _to_ref(pnl_data["realized_pnl"])
    total_unrealized = _to_ref(pnl_data["unrealized_pnl"])
    total_pnl_f = _to_ref(pnl_data["total_pnl"])
    perf_pct = round(total_pnl_f / net_deposits * 100, 2) if net_deposits > 0 else 0.0

    # Per-asset stats for allocation
    positions = CryptoPositionRepository.list_by_client(db, client.id)
    alloc_items: list[dict] = []
    for pos in positions:
        if pos.balance <= 0:
            continue
        s = build_wallet_statistics(db, client.id, pos.asset, reference_currency=ref_currency)
        cv = float(s.get("current_value", 0))
        pnl_ = float(s.get("unrealized_pnl", 0)) + float(s.get("realized_pnl", 0))
        alloc_items.append({"asset": pos.asset, "value": cv, "pnl": round(pnl_, 2)})

    platform_dicts = [
        {
            "asset": pos.asset,
            "balance": str(pos.balance),
            "available_balance": str(pos.available_balance),
        }
        for pos in positions
        if pos.balance > 0
    ]
    merged_positions = merge_app_crypto_positions(
        platform_dicts, db, person_id=getattr(client, "person_id", None)
    )
    by_asset = {a["asset"]: a for a in alloc_items if a["asset"] != "EUR"}
    for row in merged_positions:
        asset = row.get("asset")
        if not asset:
            continue
        merged_val = float(row.get("estimated_value_eur") or 0)
        scope = row.get("portfolio_scope") or "direct"
        if asset in by_asset:
            if scope == "merged" and merged_val > 0:
                by_asset[asset]["value"] = merged_val
        elif scope == "privy" and merged_val > 0:
            alloc_items.append({"asset": asset, "value": merged_val, "pnl": 0.0})
    if fiat_balance > 0:
        alloc_items.append({"asset": "EUR", "value": fiat_balance, "pnl": 0.0})
    alloc_items.sort(key=lambda x: x["value"], reverse=True)
    for a in alloc_items:
        a["weight"] = round(a["value"] / tv_f * 100, 2) if tv_f > 0 else 0.0

    # Per-asset contributions
    contributions = []
    for a in alloc_items:
        contrib = (a["pnl"] / total_pnl_f * 100) if total_pnl_f != 0 else 0.0
        contributions.append({"asset": a["asset"], "pnl": a["pnl"], "contribution_pct": round(contrib, 2)})

    # Account-level contributions (pro-rata by value)
    crypto_sum = direct_crypto_f + bundle_total_f
    direct_pnl = total_pnl_f * (direct_crypto_f / max(crypto_sum, 0.01)) if crypto_sum > 0 else 0.0
    bundle_pnl = total_pnl_f * (bundle_total_f / max(crypto_sum, 0.01)) if crypto_sum > 0 else 0.0
    account_contributions = [
        {"account": "Compte Euro", "value": round(fiat_balance, 2), "pnl": 0.0, "contribution_pct": 0.0},
        {"account": "Crypto direct", "value": round(direct_crypto_f, 2), "pnl": round(direct_pnl, 2),
         "contribution_pct": round(direct_pnl / total_pnl_f * 100, 2) if total_pnl_f != 0 else 0.0},
        {"account": "Bundles", "value": round(bundle_total_f, 2), "pnl": round(bundle_pnl, 2),
         "contribution_pct": round(bundle_pnl / total_pnl_f * 100, 2) if total_pnl_f != 0 else 0.0},
    ]

    breakdown = {
        "fiat": round(fiat_balance, 2),
        "fiat_pct": breakdown_data["fiat_pct"],
        "crypto_direct": round(direct_crypto_f, 2),
        "crypto_direct_pct": breakdown_data["crypto_direct_pct"],
        "bundles": round(bundle_total_f, 2),
        "bundles_pct": breakdown_data["bundles_pct"],
        "privy": round(_to_ref(privy_eur), 2),
    }

    # Cashflow
    acc = db.query(_CA).filter(_CA.client_id == client.id, _CA.currency == "EUR").first()
    deposits_total = D("0")
    withdrawals_total = D("0")
    deposit_count = 0
    withdrawal_count = 0
    if acc:
        deposits_total = D(str(
            db.query(func.coalesce(func.sum(_CT.amount), 0))
            .filter(
                _CT.account_id == acc.id, _CT.direction == _TD.CREDIT.value, _CT.status == "completed",
                _or(_CT.transaction_kind == _TK.BANK_TRANSFER_IN.value,
                    (_CT.transaction_kind.is_(None)) & (_CT.transaction_type == _TT.DEPOSIT.value)),
            ).scalar()
        ))
        withdrawals_total = D(str(
            db.query(func.coalesce(func.sum(_CT.amount), 0))
            .filter(
                _CT.account_id == acc.id, _CT.direction == _TD.DEBIT.value, _CT.status == "completed",
                _or(_CT.transaction_kind == _TK.BANK_TRANSFER_OUT.value,
                    (_CT.transaction_kind.is_(None)) & (_CT.transaction_type == _TT.WITHDRAWAL.value)),
            ).scalar()
        ))
        deposit_count = db.query(func.count(_CT.id)).filter(
            _CT.account_id == acc.id, _CT.direction == _TD.CREDIT.value, _CT.status == "completed",
            _or(_CT.transaction_kind == _TK.BANK_TRANSFER_IN.value, (_CT.transaction_kind.is_(None)) & (_CT.transaction_type == _TT.DEPOSIT.value)),
        ).scalar() or 0
        withdrawal_count = db.query(func.count(_CT.id)).filter(
            _CT.account_id == acc.id, _CT.direction == _TD.DEBIT.value, _CT.status == "completed",
            _or(_CT.transaction_kind == _TK.BANK_TRANSFER_OUT.value, (_CT.transaction_kind.is_(None)) & (_CT.transaction_type == _TT.WITHDRAWAL.value)),
        ).scalar() or 0
    cashflow = {
        "deposits": _to_ref(float(deposits_total.quantize(D("0.01"), rounding=RHU))),
        "withdrawals": _to_ref(float(withdrawals_total.quantize(D("0.01"), rounding=RHU))),
        "net_flow": _to_ref(float((deposits_total - withdrawals_total).quantize(D("0.01"), rounding=RHU))),
    }

    # Activity
    all_orders = db.query(ExchangeOrder).filter(ExchangeOrder.client_id == client.id, ExchangeOrder.status == "completed").all()
    direct_trades = sum(1 for o in all_orders if (o.metadata_ or {}).get("portfolio_scope", "direct") == "direct")
    bundle_events = sum(1 for o in all_orders if (o.metadata_ or {}).get("portfolio_scope") == "bundle" and (o.metadata_ or {}).get("bundle_action") != "rebalance")
    rebalance_events = sum(1 for o in all_orders if (o.metadata_ or {}).get("bundle_action") == "rebalance")
    timestamps = [o.created_at for o in all_orders if o.created_at]
    last_activity = max(timestamps).isoformat() if timestamps else None

    # Risk
    crypto_alloc = [a for a in alloc_items if a["asset"] != "EUR" and a["weight"] > 0]
    max_asset = crypto_alloc[0]["asset"] if crypto_alloc else None
    max_pct = crypto_alloc[0]["weight"] if crypto_alloc else 0.0
    hhi = sum((a["weight"] / 100) ** 2 for a in alloc_items if a["weight"] > 0)

    return {
        "currency": ref_currency,
        "performance": {
            "current_value": round(tv_f, 2),
            "total_invested": round(net_deposits, 2),
            "total_pnl": round(total_pnl_f, 2),
            "performance_pct": perf_pct,
            "realized_pnl": total_realized,
            "unrealized_pnl": total_unrealized,
        },
        "allocation": alloc_items,
        "contributions": contributions,
        "account_contributions": account_contributions,
        "breakdown": breakdown,
        "cashflow": cashflow,
        "activity": {
            "direct_trades": direct_trades,
            "bundle_invest_events": bundle_events,
            "rebalance_events": rebalance_events,
            "deposit_count": deposit_count,
            "withdrawal_count": withdrawal_count,
            "last_activity": last_activity,
        },
        "risk": {
            "assets_count": len(alloc_items),
            "concentration_asset": max_asset,
            "concentration_pct": round(max_pct, 2),
            "hhi": round(hhi, 4),
        },
    }


@bootstrap_router.get("/portfolio/global/history")
def get_global_portfolio_history(
    period: str = Query("ALL"),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Global equity curve — delegates to valuation.build_global_history."""
    from services.portfolio_engine.valuation import build_global_history

    return build_global_history(db, client.id, period=period)


# ---------------------------------------------------------------------------
# Mobile exchange endpoints (preview + buy)
# ---------------------------------------------------------------------------
_exchange_svc = _ExchangeService()


class _MobileBuyPreviewRequest(BaseModel):
    asset: str
    amount_fiat: float


class _MobileBuyRequest(BaseModel):
    asset: str
    amount_fiat: float


@bootstrap_router.post("/exchange/buy/preview")
def mobile_buy_preview(
    payload: _MobileBuyPreviewRequest,
    db: Session = Depends(get_db),
    _client: PeClient = Depends(mobile_app_client),
):
    """Compute a buy preview for the current bootstrap client.

    Uses the exact same pricing logic as the real exchange buy engine
    (ask price, spread, fees, FX conversion).
    """
    from decimal import Decimal
    try:
        result = _exchange_svc.preview_buy(
            db, payload.asset, Decimal(str(payload.amount_fiat)),
        )
        return result
    except _ExchangeError as exc:
        _raise_exchange_error(exc)


@bootstrap_router.post("/exchange/buy")
def mobile_buy(
    payload: _MobileBuyRequest,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Execute a real BUY order for the current bootstrap client.

    Generates a unique external_reference and delegates to the full exchange engine.
    """
    import uuid
    from decimal import Decimal
    from services.portfolio_engine.hardening.security.context import ActorContext as _AC

    ext_ref = f"mobile-buy-{uuid.uuid4()}"
    buy_payload = _ExchangeBuyRequest(
        client_id=client.id,
        asset=payload.asset.upper(),
        fiat_amount=Decimal(str(payload.amount_fiat)),
        currency="EUR",
        external_reference=ext_ref,
    )
    actor = _AC(actor_type="system", actor_id="mobile-app", roles=["admin"])

    try:
        result = _exchange_svc.buy(db, buy_payload, actor)
        db.commit()
        _simulate_trade_latency()
        _safe = {}
        for k, v in result.items():
            _safe[k] = str(v) if hasattr(v, 'quantize') or isinstance(v, (Decimal,)) else v
            if isinstance(v, uuid.UUID):
                _safe[k] = str(v)
        return _safe
    except _ClientNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except _ExchangeError as exc:
        _raise_exchange_error(exc)


class _MobileSellPreviewRequest(BaseModel):
    asset: str
    amount_crypto: float


class _MobileSellRequest(BaseModel):
    asset: str
    amount_crypto: float


@bootstrap_router.post("/exchange/sell/preview")
def mobile_sell_preview(
    payload: _MobileSellPreviewRequest,
    db: Session = Depends(get_db),
    _client: PeClient = Depends(mobile_app_client),
):
    """Compute a sell preview for the current bootstrap client."""
    from decimal import Decimal
    try:
        result = _exchange_svc.preview_sell(
            db, payload.asset, Decimal(str(payload.amount_crypto)),
        )
        return result
    except _ExchangeError as exc:
        _raise_exchange_error(exc)


@bootstrap_router.post("/exchange/sell")
def mobile_sell(
    payload: _MobileSellRequest,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Execute a real SELL order for the current bootstrap client."""
    import uuid
    from decimal import Decimal
    from services.portfolio_engine.hardening.security.context import ActorContext as _AC

    ext_ref = f"mobile-sell-{uuid.uuid4()}"
    sell_payload = _ExchangeSellRequest(
        client_id=client.id,
        asset=payload.asset.upper(),
        amount_crypto=Decimal(str(payload.amount_crypto)),
        currency="EUR",
        external_reference=ext_ref,
    )
    actor = _AC(actor_type="system", actor_id="mobile-app", roles=["admin"])

    try:
        result = _exchange_svc.sell(db, sell_payload, actor)
        db.commit()
        _simulate_trade_latency()
        _safe = {}
        for k, v in result.items():
            _safe[k] = str(v) if hasattr(v, 'quantize') or isinstance(v, (Decimal,)) else v
            if isinstance(v, uuid.UUID):
                _safe[k] = str(v)
        return _safe
    except _ClientNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except _ExchangeError as exc:
        _raise_exchange_error(exc)


class _SwapPreviewPayload(BaseModel):
    from_asset: str
    to_asset: str
    amount_from: float


class _SwapPayload(BaseModel):
    from_asset: str
    to_asset: str
    amount_from: float


@bootstrap_router.post("/exchange/swap/preview")
def mobile_swap_preview(
    payload: _SwapPreviewPayload,
    db: Session = Depends(get_db),
    _client: PeClient = Depends(mobile_app_client),
):
    """Compute a swap preview for the current bootstrap client."""
    from decimal import Decimal
    try:
        result = _exchange_svc.preview_swap(
            db,
            _SwapPreviewRequest(
                from_asset=payload.from_asset.upper(),
                to_asset=payload.to_asset.upper(),
                amount_from=Decimal(str(payload.amount_from)),
            ),
        )
        return result
    except _ExchangeError as exc:
        _raise_exchange_error(exc)


@bootstrap_router.post("/exchange/swap")
def mobile_swap(
    payload: _SwapPayload,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Execute a crypto ↔ crypto swap for the current bootstrap client."""
    import uuid
    from decimal import Decimal
    from services.portfolio_engine.hardening.security.context import ActorContext as _AC

    ext_ref = f"mobile-swap-{uuid.uuid4()}"
    swap_payload = _SwapRequest(
        from_asset=payload.from_asset.upper(),
        to_asset=payload.to_asset.upper(),
        amount_from=Decimal(str(payload.amount_from)),
        external_reference=ext_ref,
    )
    actor = _AC(actor_type="system", actor_id="mobile-app", roles=["admin"])

    try:
        result = _exchange_svc.swap(db, client.id, swap_payload, actor)
        db.commit()
        _simulate_trade_latency()
        _safe = {}
        for k, v in result.items():
            _safe[k] = str(v) if hasattr(v, 'quantize') or isinstance(v, (Decimal,)) else v
            if isinstance(v, uuid.UUID):
                _safe[k] = str(v)
        return _safe
    except _ClientNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except _ExchangeError as exc:
        _raise_exchange_error(exc)


# ---------------------------------------------------------------------------
# Sell-all: liquidate all crypto positions
# ---------------------------------------------------------------------------

@bootstrap_router.post("/exchange/sell-all/preview")
def mobile_sell_all_preview(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Preview selling 100% of all crypto positions for the current bootstrap client."""
    try:
        return _exchange_svc.preview_sell_all(db, client.id)
    except _ExchangeError as exc:
        _raise_exchange_error(exc)


@bootstrap_router.post("/exchange/sell-all")
def mobile_sell_all(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Execute sell-all for the current bootstrap client (sequential, best-effort)."""
    from services.portfolio_engine.hardening.security.context import ActorContext as _AC
    actor = _AC(actor_type="system", actor_id="mobile-app", roles=["admin"])

    try:
        result = _exchange_svc.sell_all(db, client.id, actor)
        db.commit()
        return result
    except _ClientNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except _ExchangeError as exc:
        _raise_exchange_error(exc)


# ---------------------------------------------------------------------------
# Bundle catalog: enriched with client portfolio IDs
# ---------------------------------------------------------------------------

@bootstrap_router.get("/bundle/catalog")
def mobile_bundle_catalog(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Return investable bundle products enriched with the client's portfolio IDs.

    Auto-provisions missing bundle portfolios for the bootstrap client so that
    every public+active bundle product is immediately investable.
    """
    from services.portfolio_engine.products.catalog import CatalogService
    from services.portfolio_engine.portfolios.models import Portfolio
    from services.portfolio_engine.templates.models import (
        PortfolioTemplate,
        TemplateAllocation,
    )
    from services.portfolio_engine.allocations.models import TargetAllocation

    catalog = CatalogService()
    items = catalog.get_public_catalog(db, product_type="crypto_bundle")

    portfolios = (
        db.query(Portfolio)
        .filter(
            Portfolio.client_id == client.id,
            Portfolio.portfolio_type == "bundle_portfolio",
            Portfolio.status == "active",
        )
        .all()
    )
    portfolio_map = {
        str(p.origin_product_id): str(p.id)
        for p in portfolios
        if p.origin_product_id is not None
    }

    # Auto-provision: create missing bundle portfolios for the bootstrap client
    provisioned_any = False
    for item in items:
        if str(item.id) in portfolio_map:
            continue

        template = (
            db.query(PortfolioTemplate)
            .filter(
                PortfolioTemplate.product_id == item.id,
                PortfolioTemplate.provisioned_portfolio_type == "bundle_portfolio",
            )
            .first()
        )
        if template is None:
            continue

        portfolio = Portfolio(
            client_id=client.id,
            origin_product_id=item.id,
            portfolio_type="bundle_portfolio",
            name=item.name,
            base_currency=template.base_currency,
            risk_profile=template.risk_profile,
            status="active",
            metadata_={
                "auto_provisioned": True,
                "provisioned_from_template": str(template.id),
            },
        )
        db.add(portfolio)
        db.flush()

        tpl_allocs = (
            db.query(TemplateAllocation)
            .filter(TemplateAllocation.template_id == template.id)
            .all()
        )
        for ta in tpl_allocs:
            db.add(TargetAllocation(
                portfolio_id=portfolio.id,
                sleeve_id=None,
                instrument_id=ta.instrument_id,
                target_weight=ta.target_weight,
                min_weight=ta.min_weight,
                max_weight=ta.max_weight,
                rebalance_priority=ta.allocation_priority,
            ))

        portfolio_map[str(item.id)] = str(portfolio.id)
        provisioned_any = True

    if provisioned_any:
        db.commit()

    enriched = []
    for item in items:
        d = item.model_dump(mode="json")
        d["portfolio_id"] = portfolio_map.get(str(item.id))
        enriched.append(d)

    return {"items": enriched, "total": len(enriched)}


# ---------------------------------------------------------------------------
# My Bundles: client-owned bundle portfolios with live valuation
# ---------------------------------------------------------------------------

@bootstrap_router.get("/bundle/my-bundles")
def mobile_my_bundles(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Return the client's bundle portfolios with positions and market values (EUR)."""
    from decimal import Decimal as D, ROUND_HALF_UP as RHU
    from services.portfolio_engine.portfolios.models import Portfolio
    from services.portfolio_engine.positions.models import PositionAtom
    from services.portfolio_engine.instruments.models import Instrument
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.allocations.models import TargetAllocation
    from services.portfolio_engine.bundle_execution.bundle_position_valuation import (
        eur_cost_basis_to_usd,
        resolve_bundle_position_market_values,
    )
    from services.market_data.fx import get_eurusdt_rate

    eurusdt_rate = get_eurusdt_rate(db, strict=False)

    portfolios = (
        db.query(Portfolio)
        .filter(
            Portfolio.client_id == client.id,
            Portfolio.portfolio_type == "bundle_portfolio",
            Portfolio.status == "active",
        )
        .all()
    )

    bundles = []
    for portfolio in portfolios:
        atoms = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio.id,
                PositionAtom.status == "open",
            )
            .all()
        )

        target_allocs = (
            db.query(TargetAllocation)
            .filter(TargetAllocation.portfolio_id == portfolio.id)
            .all()
        )
        target_weight_by_instrument = {
            ta.instrument_id: float(ta.target_weight) for ta in target_allocs
        }

        total_cost = D("0")
        total_cost_usd = D("0")
        total_market = D("0")
        total_market_usd = D("0")
        positions = []
        assets_count = 0
        seen_instrument_ids: set = set()

        for atom in atoms:
            instrument = atom.instrument or (
                db.query(Instrument).filter(Instrument.id == atom.instrument_id).first()
            )
            asset_obj = (
                db.query(Asset).filter(Asset.id == instrument.asset_id).first()
                if instrument else None
            )
            symbol = asset_obj.symbol if asset_obj else "?"
            qty = D(str(atom.quantity or 0))
            cost = D(str(atom.cost_basis or 0))
            total_cost += cost
            total_cost_usd += eur_cost_basis_to_usd(cost, eurusdt_rate)

            valuation = resolve_bundle_position_market_values(
                db,
                symbol=symbol,
                quantity=qty,
                instrument_id=atom.instrument_id,
                eurusdt_rate=eurusdt_rate,
            )
            price_eur = valuation["price_eur"]
            price_usd = valuation["price_usd"]
            market_value = valuation["market_value"]
            market_value_usd = valuation["market_value_usd"]
            if market_value is not None:
                total_market += market_value
            if market_value_usd is not None:
                total_market_usd += market_value_usd

            if atom.position_type == "spot":
                assets_count += 1
                seen_instrument_ids.add(atom.instrument_id)

            tw = target_weight_by_instrument.get(atom.instrument_id)

            positions.append({
                "asset": symbol,
                "quantity": float(qty),
                "cost_basis": float(cost),
                "cost_basis_usd": float(eur_cost_basis_to_usd(cost, eurusdt_rate)),
                "market_value": float(market_value) if market_value is not None else None,
                "market_value_usd": float(market_value_usd) if market_value_usd is not None else None,
                "price_eur": float(price_eur) if price_eur is not None else None,
                "price_usd": float(price_usd) if price_usd is not None else None,
                "position_type": atom.position_type,
                "target_weight": tw,
            })

        for ta in target_allocs:
            if ta.instrument_id in seen_instrument_ids:
                continue
            instrument = (
                db.query(Instrument).filter(Instrument.id == ta.instrument_id).first()
            )
            if not instrument:
                continue
            asset_obj = (
                db.query(Asset).filter(Asset.id == instrument.asset_id).first()
            )
            symbol = asset_obj.symbol if asset_obj else "?"
            positions.append({
                "asset": symbol,
                "quantity": 0.0,
                "cost_basis": 0.0,
                "cost_basis_usd": 0.0,
                "market_value": 0.0,
                "market_value_usd": 0.0,
                "price_eur": None,
                "price_usd": None,
                "position_type": "spot",
                "target_weight": float(ta.target_weight),
            })
            assets_count += 1

        has_holdings = any(
            D(str(a.quantity or 0)) > 0 for a in atoms
        )

        perf_pct = None
        if total_cost > 0 and total_market > 0:
            perf_pct = float(((total_market - total_cost) / total_cost) * 100)

        bundles.append({
            "portfolio_id": str(portfolio.id),
            "portfolio_name": portfolio.name,
            "origin_product_id": str(portfolio.origin_product_id) if portfolio.origin_product_id else None,
            "status": portfolio.status,
            "assets_count": assets_count,
            "total_cost_basis": float(total_cost),
            "total_cost_basis_usd": float(total_cost_usd.quantize(D("0.01"), rounding=RHU)),
            "total_market_value": float(total_market) if total_market > 0 else None,
            "total_market_value_usd": float(total_market_usd) if total_market_usd > 0 else None,
            "performance_pct": perf_pct,
            "has_holdings": has_holdings,
            "positions": positions,
        })

    return {"bundles": bundles, "total": len(bundles)}


# ---------------------------------------------------------------------------
# Bundle Orchestrator: invest into a bundle
# ---------------------------------------------------------------------------

@bootstrap_router.get("/bundle/invest/active-lock")
def mobile_bundle_invest_active_lock(
    portfolio_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Verrou investissement LI.FI en cours (reprise Portal après refresh) — lecture seule."""
    from uuid import UUID as _UUID

    from services.portfolio_engine.bundles.bundle_invest_lock import peek_bundle_invest_lock_state

    try:
        pid = _UUID(str(portfolio_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    return peek_bundle_invest_lock_state(
        db,
        client_id=client.id,
        portfolio_id=pid,
    )


@bootstrap_router.get("/bundle/reconciliation-state")
def mobile_bundle_reconciliation_state(
    portfolio_id: str,
    batch_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """État read-only d'un batch invest partiel (R4.5-E.2-A) — aucune mutation."""
    from uuid import UUID as _UUID

    from services.portfolio_engine.bundles.bundle_reconciliation_read_model import (
        BundleReconciliationNotFoundError,
        build_bundle_reconciliation_state,
    )

    try:
        pid = _UUID(str(portfolio_id))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid portfolio_id",
        )
    batch = str(batch_id or "").strip()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="batch_id_required",
        )

    try:
        return build_bundle_reconciliation_state(
            db,
            client_id=client.id,
            portfolio_id=pid,
            batch_id=batch,
        )
    except BundleReconciliationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@bootstrap_router.post("/bundle/invest")
def mobile_bundle_invest(
    payload: dict,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Invest into a bundle portfolio for the current bootstrap client.

    Expected payload::

        {
            "portfolio_id": "uuid",
            "funding_asset": "EUR",
            "funding_amount": 1000.0
        }
    """
    from decimal import Decimal as _Dec
    from services.portfolio_engine.bundles.orchestrator import (
        BundleOrchestrator,
        BundleOrchestratorError,
    )

    portfolio_id = payload.get("portfolio_id")
    funding_asset = payload.get("funding_asset", "EUR")
    funding_amount = payload.get("funding_amount")

    if not portfolio_id or not funding_amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="portfolio_id and funding_amount are required",
        )

    try:
        from uuid import UUID as _UUID
        pid = _UUID(str(portfolio_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    from services.portfolio_engine.bundles.bundle_invest_lock import BundleInvestAlreadyPendingError
    from services.portfolio_engine.bundles.bundle_v3_deposit_flow import (
        V3DepositFlowError,
        bundle_v3_deposit_flow_enabled,
        request_v3_bundle_deposit,
    )
    from services.portfolio_engine.bundles.legacy_bundle_global_lock import (
        transaction_in_progress_response_body,
    )
    from services.portfolio_engine.financial_operations.exceptions import (
        PortfolioFinancialOperationInProgress409,
    )
    from services.product_locks.exceptions import TransactionInProgress409

    orchestrator = BundleOrchestrator()
    try:
        if bundle_v3_deposit_flow_enabled():
            result = request_v3_bundle_deposit(
                db,
                client_id=client.id,
                portfolio_id=pid,
                funding_asset=funding_asset,
                funding_amount=_Dec(str(funding_amount)),
            )
        else:
            result = orchestrator.invest_into_bundle(
                db,
                client_id=client.id,
                portfolio_id=pid,
                funding_asset=funding_asset,
                funding_amount=_Dec(str(funding_amount)),
            )
        db.commit()
        return result
    except V3DepositFlowError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.code)
    except PortfolioFinancialOperationInProgress409 as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )
    except TransactionInProgress409 as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=transaction_in_progress_response_body(exc),
        )
    except BundleInvestAlreadyPendingError as exc:
        db.rollback()
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=exc.to_response())
    except BundleOrchestratorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except _ExchangeError as exc:
        _raise_exchange_error(exc)


@bootstrap_router.post("/bundle/invest/resume")
def mobile_bundle_invest_resume(
    payload: dict,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Reprend un batch invest LI.FI en cours (legs pending, cash leg déjà alimenté)."""
    from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
        resume_disabled_for_v3_deposit_flow,
    )
    from services.portfolio_engine.bundles.orchestrator import (
        BundleExpiredInvestLegsError,
        BundleOrchestrator,
        BundleOrchestratorError,
    )

    portfolio_id = payload.get("portfolio_id")
    if not portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="portfolio_id is required",
        )

    try:
        from uuid import UUID as _UUID
        pid = _UUID(str(portfolio_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    if resume_disabled_for_v3_deposit_flow(
        db,
        client_id=client.id,
        portfolio_id=pid,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "status": "v3_deposit_flow_resume_disabled",
                "error_code": "v3_deposit_flow_resume_disabled",
                "message": "Legacy resume is disabled for new V3 deposit flow.",
            },
        )

    from services.portfolio_engine.bundles.legacy_bundle_global_lock import (
        transaction_in_progress_response_body,
    )
    from services.product_locks.exceptions import TransactionInProgress409

    orchestrator = BundleOrchestrator()
    try:
        result = orchestrator.resume_lifi_invest_batch(
            db,
            client_id=client.id,
            portfolio_id=pid,
        )
        db.commit()
        return result
    except TransactionInProgress409 as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=transaction_in_progress_response_body(exc),
        )
    except BundleExpiredInvestLegsError as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )
    except BundleOrchestratorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@bootstrap_router.post("/bundle/invest/requote-expired")
def mobile_bundle_invest_requote_expired(
    payload: dict,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Re-quote buy-only du cash leg après legs invest LI.FI expirées (legacy bundle)."""
    from services.portfolio_engine.bundles.orchestrator import (
        BundleOrchestrator,
        BundleOrchestratorError,
    )

    portfolio_id = payload.get("portfolio_id")
    if not portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="portfolio_id is required",
        )

    try:
        from uuid import UUID as _UUID
        pid = _UUID(str(portfolio_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    from services.portfolio_engine.bundles.legacy_bundle_global_lock import (
        transaction_in_progress_response_body,
    )
    from services.product_locks.exceptions import TransactionInProgress409

    orchestrator = BundleOrchestrator()
    try:
        result = orchestrator.requote_expired_invest_legs(
            db,
            client_id=client.id,
            portfolio_id=pid,
        )
        db.commit()
        return result
    except TransactionInProgress409 as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=transaction_in_progress_response_body(exc),
        )
    except BundleOrchestratorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@bootstrap_router.post("/bundle/invest/preview")
def mobile_bundle_invest_preview(
    payload: dict,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Preview a bundle investment — read-only, zero side-effects.

    Expected payload::

        {
            "portfolio_id": "uuid",
            "funding_asset": "EUR",
            "funding_amount": 1000.0
        }
    """
    from decimal import Decimal as _Dec
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    portfolio_id = payload.get("portfolio_id")
    funding_asset = payload.get("funding_asset", "EUR")
    funding_amount = payload.get("funding_amount")

    if not portfolio_id or not funding_amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="portfolio_id and funding_amount are required",
        )

    try:
        from uuid import UUID as _UUID
        pid = _UUID(str(portfolio_id))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid portfolio_id",
        )

    orchestrator = BundleOrchestrator()
    return orchestrator.preview_invest(
        db,
        client_id=client.id,
        portfolio_id=pid,
        funding_asset=funding_asset,
        funding_amount=_Dec(str(funding_amount)),
    )


@bootstrap_router.post("/bundle/withdraw")
def mobile_bundle_withdraw(
    payload: dict,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Retrait bundle — unwind spot → cash leg puis release vers self-trading.

    Payload::

        {
            "portfolio_id": "uuid",
            "withdraw_amount": 50.0,
            "full_withdraw": false
        }
    """
    from decimal import Decimal as _Dec
    from services.portfolio_engine.bundles.withdraw import (
        BundleWithdrawOrchestrator,
        BundleWithdrawOrchestratorError,
    )
    from services.portfolio_engine.bundles.bundle_withdraw_lock import (
        BundleWithdrawAlreadyPendingError,
    )
    from services.portfolio_engine.financial_operations.exceptions import (
        PortfolioFinancialOperationInProgress409,
    )

    portfolio_id = payload.get("portfolio_id")
    withdraw_amount = payload.get("withdraw_amount")
    full_withdraw = payload.get("full_withdraw") is True

    if not portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="portfolio_id is required",
        )
    if not full_withdraw and not withdraw_amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="withdraw_amount is required unless full_withdraw=true",
        )

    try:
        from uuid import UUID as _UUID
        pid = _UUID(str(portfolio_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    orchestrator = BundleWithdrawOrchestrator()
    try:
        result = orchestrator.withdraw_from_bundle(
            db,
            client_id=client.id,
            portfolio_id=pid,
            withdraw_amount=_Dec(str(withdraw_amount)) if withdraw_amount is not None else None,
            full_withdraw=full_withdraw,
        )
        db.commit()
        return result
    except PortfolioFinancialOperationInProgress409 as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )
    except BundleWithdrawAlreadyPendingError as exc:
        db.rollback()
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=exc.to_response())
    except BundleWithdrawOrchestratorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@bootstrap_router.post("/bundle/withdraw/finalize")
def mobile_bundle_withdraw_finalize(
    payload: dict,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Finalise un batch retrait après confirmation des legs Li.FI."""
    from services.portfolio_engine.bundles.withdraw import BundleWithdrawOrchestrator

    portfolio_id = payload.get("portfolio_id")
    batch_id = payload.get("batch_id")
    if not portfolio_id or not batch_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="portfolio_id and batch_id are required",
        )
    try:
        from uuid import UUID as _UUID
        pid = _UUID(str(portfolio_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    orchestrator = BundleWithdrawOrchestrator()
    result = orchestrator.finalize_withdraw_batch(
        db,
        client_id=client.id,
        portfolio_id=pid,
        batch_id=str(batch_id),
    )
    db.commit()
    return result


@bootstrap_router.get("/bundle/withdraw/active-lock")
def mobile_bundle_withdraw_active_lock(
    portfolio_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Verrou retrait bundle en cours (reprise Portal après refresh)."""
    from uuid import UUID as _UUID

    from services.portfolio_engine.bundles.bundle_withdraw_lock import (
        get_active_withdraw_lock_for_portfolio,
    )

    try:
        pid = _UUID(str(portfolio_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    lock = get_active_withdraw_lock_for_portfolio(
        db, client_id=client.id, portfolio_id=pid,
    )
    if lock is None:
        return {"status": "none"}
    return {
        "status": "active",
        "lock": lock,
    }


# ---------------------------------------------------------------------------
# Direct Portfolio Overlay: backfill + invariant F + scoped positions
# ---------------------------------------------------------------------------

@bootstrap_router.post("/direct-portfolio/backfill")
def mobile_direct_portfolio_backfill(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Backfill direct portfolio atoms from crypto_positions minus bundle atoms."""
    from services.portfolio_engine.direct_overlay import backfill_direct_atoms

    result = backfill_direct_atoms(db, client.id)
    db.commit()
    return result


@bootstrap_router.get("/orders/scope-metadata-diagnostic")
def mobile_order_scope_metadata_diagnostic(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Diagnostic: count orders by scope metadata status.

    Returns totals for tagged/untagged/invalid orders so we can verify
    the backfill is complete before removing legacy fallback branches.
    """
    from services.exchange.models import ExchangeOrder

    orders = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client.id,
            ExchangeOrder.status == "completed",
        )
        .all()
    )

    total = len(orders)
    tagged = 0
    untagged_scope = 0
    untagged_id = 0
    invalid = 0
    by_scope = {"direct": 0, "bundle": 0, "other": 0}
    untagged_samples = []

    for o in orders:
        meta = dict(o.metadata_ or {})
        scope = meta.get("portfolio_scope")
        pid = meta.get("portfolio_id")

        if not scope:
            untagged_scope += 1
            if len(untagged_samples) < 5:
                untagged_samples.append({
                    "order_id": str(o.id),
                    "external_reference": o.external_reference,
                    "metadata_keys": list(meta.keys()),
                })
        if not pid:
            untagged_id += 1

        if scope and not pid:
            invalid += 1
        elif scope == "bundle" and not meta.get("portfolio_id"):
            invalid += 1

        if scope:
            tagged += 1
            by_scope[scope] = by_scope.get(scope, 0) + 1

    return {
        "status": "ok",
        "total_completed_orders": total,
        "tagged": tagged,
        "untagged_scope": untagged_scope,
        "untagged_portfolio_id": untagged_id,
        "invalid": invalid,
        "by_scope": by_scope,
        "ready_for_cleanup": untagged_scope == 0 and invalid == 0,
        "untagged_samples": untagged_samples,
    }


@bootstrap_router.post("/orders/backfill-scope-metadata")
def mobile_backfill_order_scope_metadata(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Backfill portfolio_scope / portfolio_id in exchange_orders.metadata_.

    For each completed order of the current client:
    - If metadata_ already has portfolio_scope → skip (idempotent).
    - If metadata_ has bundle_id → set portfolio_scope=bundle, portfolio_id=bundle_id.
    - Otherwise → set portfolio_scope=direct, portfolio_id=direct_portfolio.id.
    """
    from services.exchange.models import ExchangeOrder
    from services.portfolio_engine.direct_overlay import ensure_direct_portfolio

    direct_pf = ensure_direct_portfolio(db, client.id)
    direct_pf_id = str(direct_pf.id)

    orders = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client.id,
            ExchangeOrder.status == "completed",
        )
        .all()
    )

    stats = {"total": len(orders), "already_tagged": 0, "tagged_direct": 0, "tagged_bundle": 0}

    for order in orders:
        meta = dict(order.metadata_ or {})
        if meta.get("portfolio_scope"):
            stats["already_tagged"] += 1
            continue

        bundle_id = meta.get("bundle_id")
        if bundle_id:
            meta["portfolio_scope"] = "bundle"
            meta["portfolio_id"] = str(bundle_id)
            stats["tagged_bundle"] += 1
        else:
            meta["portfolio_scope"] = "direct"
            meta["portfolio_id"] = direct_pf_id
            stats["tagged_direct"] += 1

        order.metadata_ = meta

    db.flush()
    db.commit()

    return {"status": "ok", "backfill": stats}


@bootstrap_router.get("/direct-portfolio/invariant-f")
def mobile_direct_invariant_f(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Check invariant F: direct + bundle atoms ≈ crypto_positions per asset."""
    from services.portfolio_engine.direct_overlay import check_invariant_f

    return check_invariant_f(db, client.id)


@bootstrap_router.get("/bundle/invariant-d")
def mobile_bundle_invariant_d(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Check invariant D: PE atoms ≤ crypto positions."""
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    return BundleOrchestrator.check_invariant_d(db, client.id)


@bootstrap_router.get("/bundle/{portfolio_id}/status")
def mobile_bundle_status(
    portfolio_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Get the current state of a bundle: cash leg + allocated positions."""
    from services.portfolio_engine.bundles.orchestrator import (
        BundleOrchestrator,
        BundleOrchestratorError,
    )

    try:
        from uuid import UUID as _UUID
        pid = _UUID(portfolio_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    try:
        return BundleOrchestrator.get_bundle_status(db, pid, client.id)
    except BundleOrchestratorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@bootstrap_router.get("/bundle/{portfolio_id}/statistics")
def mobile_bundle_statistics(
    portfolio_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Portfolio-level statistics for a bundle: performance, allocation, contribution, risk."""
    from decimal import Decimal as D, ROUND_HALF_UP as RHU
    from uuid import UUID as _UUID

    from services.portfolio_engine.portfolios.models import Portfolio
    from services.portfolio_engine.positions.models import PositionAtom
    from services.portfolio_engine.instruments.models import Instrument
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.allocations.models import TargetAllocation
    from services.portfolio_engine.instruments.price_bridge import get_instrument_price
    from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
    from services.exchange.models import ExchangeOrder

    try:
        pid = _UUID(portfolio_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    portfolio = db.query(Portfolio).filter(Portfolio.id == pid).first()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="portfolio_not_found")

    eurusdt_rate = get_eurusdt_rate(db, strict=False)

    atoms = (
        db.query(PositionAtom)
        .filter(PositionAtom.portfolio_id == pid, PositionAtom.status == "open")
        .all()
    )

    target_allocs = (
        db.query(TargetAllocation)
        .filter(TargetAllocation.portfolio_id == pid)
        .all()
    )
    target_weight_map = {ta.instrument_id: float(ta.target_weight) for ta in target_allocs}

    total_cost = D("0")
    total_market = D("0")
    cash_value = D("0")
    cash_cost = D("0")
    asset_details: list[dict] = []
    seen_instruments: set = set()

    for atom in atoms:
        instrument = atom.instrument or db.query(Instrument).filter(Instrument.id == atom.instrument_id).first()
        asset_obj = db.query(Asset).filter(Asset.id == instrument.asset_id).first() if instrument else None
        symbol = asset_obj.symbol.upper() if asset_obj else "?"
        qty = D(str(atom.quantity or 0))
        cost = D(str(atom.cost_basis or 0))
        total_cost += cost

        price_eur = None
        market_value = None
        try:
            price_info = get_instrument_price(db, atom.instrument_id)
            price_usdt = D(price_info["price"]) if price_info.get("price") else None
            if price_usdt is not None:
                price_eur = usdt_to_eur(price_usdt, eurusdt_rate)
                if qty > 0:
                    market_value = (qty * price_eur).quantize(D("0.01"), rounding=RHU)
                    total_market += market_value
        except Exception:
            pass

        if atom.position_type == "cash":
            if market_value is not None:
                cash_value += market_value
            cash_cost += cost
        elif atom.position_type == "spot":
            seen_instruments.add(atom.instrument_id)
            pnl = float(market_value - cost) if market_value is not None else None
            asset_details.append({
                "asset": symbol,
                "quantity": float(qty),
                "cost_basis": float(cost),
                "market_value": float(market_value) if market_value is not None else None,
                "pnl": pnl,
                "target_weight": target_weight_map.get(atom.instrument_id),
            })

    for ta in target_allocs:
        if ta.instrument_id in seen_instruments:
            continue
        instrument = db.query(Instrument).filter(Instrument.id == ta.instrument_id).first()
        asset_obj = db.query(Asset).filter(Asset.id == instrument.asset_id).first() if instrument else None
        symbol = asset_obj.symbol.upper() if asset_obj else "?"
        asset_details.append({
            "asset": symbol,
            "quantity": 0.0,
            "cost_basis": 0.0,
            "market_value": 0.0,
            "pnl": 0.0,
            "target_weight": float(ta.target_weight),
        })

    total_pnl = float(total_market - total_cost) if total_market > 0 else 0.0
    perf_pct = float(((total_market - total_cost) / total_cost) * 100) if total_cost > 0 and total_market > 0 else 0.0

    allocation_vs_target = []
    for ad in asset_details:
        mv = ad.get("market_value") or 0.0
        current_pct = (mv / float(total_market) * 100) if total_market > 0 else 0.0
        target_pct = (ad.get("target_weight") or 0) * 100
        allocation_vs_target.append({
            "asset": ad["asset"],
            "target_pct": round(target_pct, 2),
            "current_pct": round(current_pct, 2),
            "drift_pct": round(current_pct - target_pct, 2),
        })

    contributions = []
    for ad in asset_details:
        asset_pnl = ad.get("pnl") or 0.0
        contrib_pct = (asset_pnl / total_pnl * 100) if total_pnl != 0 else 0.0
        contributions.append({
            "asset": ad["asset"],
            "pnl": round(asset_pnl, 2),
            "contribution_pct": round(contrib_pct, 2),
        })

    invested_pct = float((total_market - cash_value) / total_market * 100) if total_market > 0 else 0.0
    cash_pct = float(cash_value / total_market * 100) if total_market > 0 else 0.0

    max_weight_asset = max(allocation_vs_target, key=lambda x: x["current_pct"])["asset"] if allocation_vs_target else None
    max_weight_pct = max(a["current_pct"] for a in allocation_vs_target) if allocation_vs_target else 0.0

    bundle_orders = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client.id,
            ExchangeOrder.metadata_["portfolio_id"].astext == portfolio_id,
            ExchangeOrder.status == "completed",
        )
        .all()
    )
    rebalance_count = sum(1 for o in bundle_orders if (o.metadata_ or {}).get("bundle_action") == "rebalance")
    total_events = len(bundle_orders)

    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        "performance": {
            "current_value": float(total_market),
            "total_invested": float(total_cost),
            "total_pnl": round(total_pnl, 2),
            "performance_pct": round(perf_pct, 2),
        },
        "allocation_vs_target": allocation_vs_target,
        "contributions": contributions,
        "cash_deployment": {
            "invested_pct": round(invested_pct, 2),
            "cash_pct": round(cash_pct, 2),
            "cash_value": float(cash_value),
        },
        "activity": {
            "rebalance_count": rebalance_count,
            "total_allocation_events": total_events,
        },
        "risk": {
            "assets_count": len(asset_details),
            "concentration_asset": max_weight_asset,
            "concentration_pct": round(max_weight_pct, 2),
        },
    }


@bootstrap_router.get("/bundle/{portfolio_id}/history")
def mobile_bundle_history(
    portfolio_id: str,
    period: str = Query("ALL", pattern="^(1D|1W|1M|ALL)$"),
    asset: Optional[str] = Query(None),
    mode: str = Query("value", pattern="^(value|performance_value)$"),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Wallet history scoped to a specific bundle portfolio."""
    from uuid import UUID as _UUID

    try:
        _UUID(portfolio_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    ref_currency = getattr(client, "reference_currency", "EUR") or "EUR"
    result = build_wallet_history(
        db, client.id, reference_currency=ref_currency,
        asset=asset.upper() if asset else None,
        mode=mode,
        portfolio_scope="bundle",
        portfolio_id=portfolio_id,
    )

    if period != "ALL" and result["points"]:
        from datetime import datetime, timedelta, timezone as tz

        now = datetime.now(tz.utc)
        delta_map = {"1D": timedelta(days=1), "1W": timedelta(weeks=1), "1M": timedelta(days=30)}
        cutoff = now - delta_map[period]
        result["points"] = [
            p for p in result["points"]
            if datetime.fromisoformat(p["timestamp"]) >= cutoff
        ]

    return result


@bootstrap_router.get("/bundle/{portfolio_id}/transactions")
def mobile_bundle_transactions(
    portfolio_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Historique bundle : swaps internes (allocation, rebalance, retrait) + entrées/sorties jambe."""
    from uuid import UUID as _UUID
    from services.portfolio_engine.bundle_execution.bundle_portfolio_transactions import (
        list_bundle_portfolio_transactions,
    )

    try:
        pid = _UUID(portfolio_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    txs = list_bundle_portfolio_transactions(
        db,
        client_id=client.id,
        person_id=getattr(client, "person_id", None),
        portfolio_id=pid,
        limit=100,
    )

    serialized = []
    for tx in txs:
        created = tx.get("created_at")
        serialized.append(
            {
                **tx,
                "id": str(tx.get("id")),
                "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
            }
        )

    return {"portfolio_id": portfolio_id, "transactions": serialized}


@bootstrap_router.get("/bundle/{portfolio_id}/ledger")
def mobile_bundle_ledger(
    portfolio_id: str,
    batch_id: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Journal bundle shadow (Phase 4A) — lecture seule, n remplace pas l'historique existant."""
    from uuid import UUID as _UUID
    from services.portfolio_engine.bundle_ledger.service import list_bundle_ledger_entries
    from services.portfolio_engine.portfolios.models import Portfolio

    try:
        pid = _UUID(portfolio_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == pid, Portfolio.client_id == client.id)
        .first()
    )
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="portfolio_not_found")

    person_id = getattr(client, "person_id", None)
    return list_bundle_ledger_entries(
        db,
        bundle_portfolio_id=pid,
        person_id=person_id,
        batch_id=batch_id,
        limit=limit,
    )


@bootstrap_router.post("/bundle/{portfolio_id}/rebalance/preview")
def mobile_bundle_rebalance_preview(
    portfolio_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Preview a bundle rebalance plan without executing anything."""
    from services.portfolio_engine.bundles.rebalance import BundleRebalanceOrchestrator

    try:
        from uuid import UUID as _UUID
        pid = _UUID(portfolio_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    try:
        orchestrator = BundleRebalanceOrchestrator()
        result = orchestrator.preview_rebalance(db, client_id=client.id, portfolio_id=pid)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@bootstrap_router.post("/bundle/{portfolio_id}/rebalance")
def mobile_bundle_rebalance_execute(
    portfolio_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Execute a bundle rebalance."""
    from services.portfolio_engine.bundles.rebalance import BundleRebalanceOrchestrator

    try:
        from uuid import UUID as _UUID
        pid = _UUID(portfolio_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    from services.portfolio_engine.bundles.bundle_invest_lock import (
        load_portfolio_for_invest_lock,
        reconcile_or_expire_idle_invest_lock,
    )

    portfolio = load_portfolio_for_invest_lock(
        db, client_id=client.id, portfolio_id=pid,
    )
    if not reconcile_or_expire_idle_invest_lock(
        db,
        client_id=client.id,
        portfolio_id=pid,
        portfolio=portfolio,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="invest_lock_active",
        )

    try:
        orchestrator = BundleRebalanceOrchestrator()
        result = orchestrator.execute_rebalance(db, client_id=client.id, portfolio_id=pid)
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@bootstrap_router.post("/bundle/{portfolio_id}/rebalance/v3/execute")
def mobile_bundle_rebalance_v3_execute(
    portfolio_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
    trigger: str = "manual",
):
    """Execute V3 drift rebalance plan (feature-flagged — n remplace pas /rebalance legacy)."""
    import os
    from uuid import UUID as _UUID

    if os.getenv("BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="v3_executor_disabled")

    from services.portfolio_engine.bundles.drift_engine import compute_bundle_drift_snapshot
    from services.portfolio_engine.bundles.rebalance_executor import (
        BundleRebalanceExecutorError,
        execute_v3_bundle_rebalance,
    )
    from services.portfolio_engine.bundles.rebalance_planner import (
        plan_bundle_rebalance_from_drift,
    )

    try:
        pid = _UUID(portfolio_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    if trigger not in ("manual", "deposit", "recovery", "cron"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_trigger")

    import uuid as _uuid_mod

    from services.portfolio_engine.financial_operations.exceptions import (
        PortfolioFinancialOperationInProgress409,
    )
    from services.portfolio_engine.financial_operations.wiring import (
        acquire_bundle_rebalance_v3_portfolio_operation,
        release_bundle_rebalance_v3_portfolio_operation,
    )

    execution_id = _uuid_mod.uuid4()
    _TERMINAL_V3_STATUSES = frozenset({
        "COMPLETED",
        "COMPLETED_WITH_RESIDUAL_CASH",
        "FAILED",
        "NO_ACTION",
    })

    try:
        acquire_bundle_rebalance_v3_portfolio_operation(
            db,
            portfolio_id=pid,
            execution_id=execution_id,
        )
        snap = compute_bundle_drift_snapshot(db, client_id=client.id, portfolio_id=pid)
        plan = plan_bundle_rebalance_from_drift(snap)
        result = execute_v3_bundle_rebalance(
            db,
            client_id=client.id,
            portfolio_id=pid,
            drift_rebalance_plan=plan,
            trigger=trigger,  # type: ignore[arg-type]
        )
        v3_status = str(result.get("v3_status") or "")
        if v3_status in _TERMINAL_V3_STATUSES:
            release_bundle_rebalance_v3_portfolio_operation(
                db,
                portfolio_id=pid,
                execution_id=execution_id,
                failed=v3_status == "FAILED",
            )
        db.commit()
        return result
    except PortfolioFinancialOperationInProgress409 as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )
    except BundleRebalanceExecutorError as exc:
        release_bundle_rebalance_v3_portfolio_operation(
            db,
            portfolio_id=pid,
            execution_id=execution_id,
            failed=True,
        )
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        release_bundle_rebalance_v3_portfolio_operation(
            db,
            portfolio_id=pid,
            execution_id=execution_id,
            failed=True,
        )
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@bootstrap_router.post("/bundle/leg/{swap_id}/prepare-sign")
def mobile_bundle_leg_prepare_sign(
    swap_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Payload de signature Privy pour un leg bundle LI.FI (après invest/rebalance pending)."""
    from uuid import UUID as _UUID

    from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService

    if client.person_id is None:
        raise HTTPException(status_code=400, detail="client_has_no_person_id")

    try:
        sid = _UUID(swap_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="invalid swap_id")

    svc = BundleLifiLegService()
    try:
        resp = svc.prepare_signing(db, person_id=client.person_id, swap_id=sid)
        return resp.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@bootstrap_router.post("/bundle/leg/{swap_id}/submit-tx")
def mobile_bundle_leg_submit_tx(
    swap_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Soumet la transaction signée ; settlement Privy + atoms PE si confirmé."""
    from decimal import Decimal as _Dec
    from uuid import UUID as _UUID

    from services.lifi.swap_repository import PersonWalletSwapRepository
    from services.portfolio_engine.bundle_execution.bundle_lifi_api import leg_from_swap_audit
    from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService

    if client.person_id is None:
        raise HTTPException(status_code=400, detail="client_has_no_person_id")

    tx_hash = (payload or {}).get("tx_hash")
    if not tx_hash:
        raise HTTPException(status_code=422, detail="tx_hash required")

    try:
        sid = _UUID(swap_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="invalid swap_id")

    swap = PersonWalletSwapRepository().get_for_person(
        db, swap_id=sid, person_id=client.person_id,
    )
    if swap is None:
        raise HTTPException(status_code=404, detail="swap_not_found")

    leg = leg_from_swap_audit(swap)
    if leg is None:
        raise HTTPException(status_code=400, detail="not_a_bundle_swap_leg")

    svc = BundleLifiLegService()
    try:
        result = svc.submit_leg_tx(
            db,
            leg=leg,
            person_id=client.person_id,
            swap_id=sid,
            tx_hash=str(tx_hash),
        )
        db.commit()
        return {
            "leg_id": result.leg_id,
            "status": result.status,
            "swap_id": str(sid),
            "tx_hash": result.tx_hash,
            "amount_to": str(result.amount_to) if result.amount_to is not None else None,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@bootstrap_router.post("/bundle/batch/finalize")
def mobile_bundle_batch_finalize(
    payload: dict,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Finalise un batch LI.FI après legs confirmés + invariant G dry-run."""
    from decimal import Decimal as _Dec
    from uuid import UUID as _UUID

    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    portfolio_id = payload.get("portfolio_id")
    batch_id = payload.get("batch_id")
    entry_instrument_id = payload.get("entry_instrument_id")
    planned_total = payload.get("planned_entry_total")
    entry_consumed = payload.get("entry_consumed", 0)

    if not all([portfolio_id, batch_id, entry_instrument_id, planned_total is not None]):
        raise HTTPException(
            status_code=422,
            detail="portfolio_id, batch_id, entry_instrument_id, planned_entry_total required",
        )

    try:
        pid = _UUID(str(portfolio_id))
        eid = _UUID(str(entry_instrument_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="invalid uuid")

    orch = BundleOrchestrator()
    try:
        out = orch.finalize_lifi_batch(
            db,
            client_id=client.id,
            portfolio_id=pid,
            batch_id=str(batch_id),
            entry_instrument_id=eid,
            planned_entry_total=_Dec(str(planned_total)),
            entry_consumed=_Dec(str(entry_consumed)),
        )
        db.commit()
        return out
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@bootstrap_router.get("/bundle/invariant-g")
def mobile_bundle_invariant_g(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Invariant G dry-run : atoms PE vs soldes Privy."""
    from services.portfolio_engine.invariants.invariant_g import check_invariant_g

    return check_invariant_g(db, client.id, dry_run=True)


@bootstrap_router.get("/bundle/{portfolio_id}/invariant-e")
def mobile_bundle_invariant_e(portfolio_id: str, db: Session = Depends(get_db)):
    """Check invariant E: cash leg + allocated cost basis consistency."""
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    try:
        from uuid import UUID as _UUID
        pid = _UUID(portfolio_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid portfolio_id")

    return BundleOrchestrator.check_invariant_e(db, pid)


# ---------------------------------------------------------------------------
# Lending / Placements
# ---------------------------------------------------------------------------

@bootstrap_router.get("/lending/earn/positions")
def mobile_lending_earn_positions(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Earn positions for the current test client (Placements screen)."""
    from services.lending.product_surface import get_earn_positions

    try:
        return get_earn_positions(db, client.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing earn positions: {exc}",
        )


@bootstrap_router.get("/lending/dashboard")
def mobile_lending_dashboard(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Combined Earn + Borrow dashboard for the current test client."""
    from services.lending.product_surface import get_earn_borrow_dashboard

    try:
        return get_earn_borrow_dashboard(db, client.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing lending dashboard: {exc}",
        )


class _LendingInvestBody(BaseModel):
    funding_asset: str
    funding_amount: float


@bootstrap_router.post("/lending/products/{product_id}/invest/preview")
def mobile_lending_invest_preview(
    product_id: str,
    body: _LendingInvestBody,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Preview invest into exclusive offer for the current test client."""
    from services.lending.invest_orchestrator import (
        LendingInvestOrchestrator,
        LendingInvestError,
    )
    from decimal import Decimal

    try:
        from uuid import UUID as _UUID
        orch = LendingInvestOrchestrator()
        return orch.preview_invest(
            db,
            product_id=_UUID(product_id),
            client_id=client.id,
            funding_asset=body.funding_asset,
            funding_amount=Decimal(str(body.funding_amount)),
        )
    except LendingInvestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error previewing lending invest: {exc}",
        )


@bootstrap_router.post("/lending/products/{product_id}/invest")
def mobile_lending_invest_execute(
    product_id: str,
    body: _LendingInvestBody,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Invest into exclusive offer for the current test client."""
    from services.lending.invest_orchestrator import (
        LendingInvestOrchestrator,
        LendingInvestError,
    )
    from decimal import Decimal

    try:
        from uuid import UUID as _UUID
        orch = LendingInvestOrchestrator()
        result = orch.invest_into_product(
            db,
            product_id=_UUID(product_id),
            client_id=client.id,
            funding_asset=body.funding_asset,
            funding_amount=Decimal(str(body.funding_amount)),
        )
        db.commit()
        return result
    except LendingInvestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing lending invest: {exc}",
        )
