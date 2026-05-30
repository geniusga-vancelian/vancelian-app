"""
Arquantix API - FastAPI REST API with PostgreSQL
Public endpoints for site vitrine + Admin endpoints with JWT auth
"""
from fastapi import FastAPI, HTTPException, Depends, status, Request, UploadFile, File, WebSocket, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
import os
import uuid
import shutil
from pathlib import Path

from database import (
    get_db, GlobalSettings, Page, News, ContactSubmission, AdminUser,
    StatusEnum, init_db
)
from schemas import (
    Token, LoginRequest, RefreshTokenRequest, RevokeTokenRequest, AuthSessionItem,
    GlobalSettingsResponse, GlobalSettingsUpdate,
    PageCreate, PageUpdate, PageResponse,
    NewsCreate, NewsUpdate, NewsResponse,
    ContactSubmissionCreate, ContactSubmissionResponse
)
from auth import (
    get_current_user,
    oauth2_scheme,
    verify_password,
    get_password_hash,
)
from services.auth.device_attestation_routes import router as device_attestation_router
from services.auth.device_credentials_routes import router as device_credentials_router
from services.auth.refresh_session import (
    perform_login,
    perform_refresh,
    perform_revoke,
    perform_revoke_all,
    list_active_sessions,
)
from services.auth.security_admin_routes import router as auth_security_admin_router
from services.security.risk_dashboard_routes import router as risk_dashboard_router
from services.auth.risk_rules_admin_routes import router as risk_rules_admin_router
from services.security.ml.fraud_ml_admin_routes import router as fraud_ml_admin_router
from services.security.device_reputation.device_reputation_admin_routes import (
    router as device_reputation_admin_router,
)
from services.auth.passkeys_routes import router as passkeys_router
from services.auth.well_known_routes import router as well_known_router
from services.auth.admin_email_otp_routes import router as admin_email_otp_router
from services.auth.adaptive_auth_routes import router as adaptive_auth_router
from services.auth.mobile_otp_login_routes import router as mobile_otp_login_router
from services.auth.signup_mobile_routes import router as signup_mobile_router
from services.auth.local_passcode_ack_routes import router as local_passcode_ack_router
from services.auth.privy_exchange_routes import router as privy_exchange_router
from services.auth.privy_signup_exchange_routes import router as privy_signup_exchange_router
from services.auth.privy_link_routes import router as privy_link_router
from services.auth.privy_person_wallets_routes import router as privy_person_wallets_router
from services.privy.solana_wallet_routes import solana_wallet_router
from services.lifi.routes import swaps_router
from services.translate import translate_page_payload
from services.bundles import router as bundles_router
from services.diagnostics import router as diagnostics_router
from services.market_data.routes import router as market_data_router
from services.backtest.routes import router as backtest_router
from services.ai_email.routes import router as ai_email_router
from services.ai_jurisdiction_configs.routes import router as ai_jurisdiction_configs_router
from services.persons.routes import router as persons_router
from services.jurisdiction_configs.routes import router as jurisdiction_configs_router
from services.onboarding.routes import router as onboarding_router
from services.aml_risk.routes import router as aml_risk_router
from services.field_definitions.routes import router as field_definitions_router
from services.finance_strategy_chat.routes import router as finance_strategy_chat_router
from services.chatbot_epargne.routes import router as chatbot_epargne_router
from services.assistance import router as assistance_router
from services.assistance.admin_knowledge_router import (
    admin_router as assistance_admin_knowledge_router,
)
from services.assistance.admin_conversations_router import (
    admin_conversations_router as assistance_admin_conversations_router,
)
from services.assistance.admin_cognitive_router import (
    admin_cognitive_router as assistance_admin_cognitive_router,
)
from services.assistance.admin_observability_router import (
    admin_observability_router as assistance_admin_observability_router,
)
from services.assistance.admin_client_discovery_router import (
    admin_client_discovery_router as assistance_admin_client_discovery_router,
)
from services.assistance.admin_action_playbooks_router import (
    admin_router as assistance_admin_action_playbooks_router,
)
from services.assistance.admin_agent_action_options_router import (
    admin_router as assistance_admin_agent_action_options_router,
)
from services.migrations.routes import router as migrations_router
from services.portfolio_engine import router as portfolio_engine_router
from services.customers_admin import customers_admin_router
from services.portfolio_engine.bundle_ledger.admin_router import bundle_ledger_admin_router
from services.test_clients import (
    bootstrap_router as test_clients_bootstrap_router,
    mobile_flutter_router as test_clients_mobile_flutter_router,
)
from services.custody import custody_admin_router, custody_transfer_router, custody_webhook_router
from services.privy_wallet.webhook_router import privy_webhook_router
from services.privy_wallet.routes import privy_wallet_app_router
from services.privy_wallet.admin_router import privy_wallet_admin_router
from services.onchain_reconciliation.admin_router import onchain_reconciliation_admin_router
from services.transaction_intents.lombard_intent_router import lombard_intent_internal_router
from services.transaction_intents.ledgity_intent_router import ledgity_intent_internal_router
from services.transaction_intents.morpho_intent_router import morpho_intent_internal_router
from services.exchange import exchange_admin_router, exchange_router
from services.price_alerts import price_alerts_router, orders_router
from services.favorites.router import router as favorites_router
from services.notifications import notifications_router
from services.lending import lending_router, wealth_router as lending_wealth_router, pool_router as lending_pool_router, interest_router as lending_interest_router, product_router as lending_product_router, offer_router as lending_offer_router
from services.registration import (
    registration_runtime_router,
    registration_admin_router,
    jurisdiction_policy_admin_router,
    jurisdiction_policy_legacy_router,
    country_directory_admin_router,
)
from services.address import address_router
from services.security import two_factor_router
from services.security.contact_submissions_crypto import (
    contact_row_to_admin_dict,
    contact_row_to_public_response_dict,
    encrypt_and_assign_contact_fields,
)
from services.security.zero_trust.request_security_context import build_request_security_context
from services.security.sensitive_action_events import record_sensitive_action_completed
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action
from services.security.zero_trust.security_guards import enforce_zero_trust_or_raise
from services.security.zero_trust.zero_trust_admin_routes import router as zero_trust_admin_router
from services.security.crypto_service import (
    crypto_feature_contact_enabled,
    is_encryption_configured,
    strip_plaintext_after_encrypt_contact,
)
from services.presentations.router import (
    presentations_router as presentation_decks_router,
    templates_router as presentation_templates_router,
    version_router as presentation_versions_router,
)
from services.portfolio_engine.clients.models import Client as _Client  # noqa: F401 — force mapper init for Person ↔ Client relationship
from services.market_data.ws_broadcast import handle_market_data_ws
from pydantic import BaseModel

# Media / uploads (used by create_app and route handlers)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "http://localhost:8011")
UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


def create_app(testing: bool = False) -> FastAPI:
    """Build FastAPI app. Use testing=True to skip non-essential startup (e.g. heavy logging)."""
    app = FastAPI(
        title="Arquantix API",
        version="2.0.0",
        description="REST API for Arquantix site vitrine + admin"
    )
    app.state.testing = testing

    from services.auth.auth_bootstrap import enforce_auth_infrastructure_bootstrap

    enforce_auth_infrastructure_bootstrap(testing=testing)

    from services.security.production_mock_guard import enforce_production_mock_guard

    enforce_production_mock_guard(testing=testing)

    from database import engine as _db_engine
    from services.auth.db_sql_metrics import install_db_sql_metrics_listener

    install_db_sql_metrics_listener(_db_engine)

    # CORS — les origines Vite (5173) sont toujours ajoutées si absentes, car CORS_ORIGINS
    # dans .env remplace sinon toute la liste par défaut et casse le design-system sur :5173.
    _cors_default = (
        "http://localhost:3001,http://localhost:3000,http://localhost:3011,"
        "http://localhost:5173,http://127.0.0.1:5173"
    )
    _cors_raw = os.getenv("CORS_ORIGINS", _cors_default)
    _cors_list = [o.strip() for o in _cors_raw.split(",") if o.strip()]
    for _extra in ("http://localhost:5173", "http://127.0.0.1:5173"):
        if _extra not in _cors_list:
            _cors_list.append(_extra)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from services.auth.auth_rate_limit_middleware import AuthRateLimitMiddleware

    app.add_middleware(AuthRateLimitMiddleware)

    from services.security.session_intelligence_middleware import SessionIntelligenceActivityMiddleware

    app.add_middleware(SessionIntelligenceActivityMiddleware)

    # Media storage (UPLOADS_DIR at module level below)
    app.mount("/media", StaticFiles(directory=str(UPLOADS_DIR)), name="media")

    # Include routers
    app.include_router(bundles_router)
    app.include_router(diagnostics_router)
    app.include_router(market_data_router)
    app.include_router(backtest_router)
    app.include_router(ai_email_router)
    app.include_router(ai_jurisdiction_configs_router)
    app.include_router(persons_router)
    app.include_router(jurisdiction_configs_router)
    app.include_router(onboarding_router)
    app.include_router(aml_risk_router)
    app.include_router(field_definitions_router)
    app.include_router(finance_strategy_chat_router)
    app.include_router(chatbot_epargne_router)
    app.include_router(assistance_router)
    app.include_router(assistance_admin_knowledge_router)
    app.include_router(assistance_admin_conversations_router)
    app.include_router(assistance_admin_cognitive_router)
    app.include_router(assistance_admin_observability_router)
    app.include_router(assistance_admin_client_discovery_router)
    app.include_router(assistance_admin_action_playbooks_router)
    app.include_router(assistance_admin_agent_action_options_router)
    app.include_router(migrations_router)
    app.include_router(portfolio_engine_router)
    app.include_router(customers_admin_router)
    app.include_router(bundle_ledger_admin_router)
    app.include_router(test_clients_bootstrap_router)
    app.include_router(test_clients_mobile_flutter_router)
    app.include_router(custody_admin_router)
    app.include_router(custody_transfer_router)
    app.include_router(custody_webhook_router)
    app.include_router(privy_webhook_router)
    app.include_router(privy_wallet_app_router)
    app.include_router(privy_wallet_admin_router)
    app.include_router(onchain_reconciliation_admin_router)
    app.include_router(morpho_intent_internal_router)
    app.include_router(ledgity_intent_internal_router)
    app.include_router(lombard_intent_internal_router)
    app.include_router(exchange_router)
    app.include_router(exchange_admin_router)
    app.include_router(price_alerts_router)
    app.include_router(orders_router)
    app.include_router(favorites_router)
    app.include_router(notifications_router)
    app.include_router(lending_router)
    app.include_router(lending_wealth_router)
    app.include_router(lending_pool_router)
    app.include_router(lending_interest_router)
    app.include_router(lending_product_router)
    app.include_router(lending_offer_router)
    app.include_router(registration_runtime_router)
    app.include_router(address_router)
    app.include_router(registration_admin_router)
    app.include_router(jurisdiction_policy_admin_router)
    app.include_router(jurisdiction_policy_legacy_router)
    app.include_router(country_directory_admin_router)
    app.include_router(two_factor_router)
    app.include_router(presentation_templates_router)
    app.include_router(presentation_decks_router)
    app.include_router(presentation_versions_router)
    app.include_router(auth_security_admin_router)
    app.include_router(risk_dashboard_router)
    app.include_router(risk_rules_admin_router)
    app.include_router(zero_trust_admin_router)
    app.include_router(fraud_ml_admin_router)
    app.include_router(device_reputation_admin_router)
    app.include_router(passkeys_router)
    app.include_router(well_known_router)
    app.include_router(admin_email_otp_router)
    app.include_router(adaptive_auth_router)
    app.include_router(mobile_otp_login_router)
    app.include_router(signup_mobile_router)
    app.include_router(local_passcode_ack_router)
    app.include_router(privy_exchange_router)
    app.include_router(privy_signup_exchange_router)
    app.include_router(privy_link_router)
    app.include_router(privy_person_wallets_router)
    app.include_router(solana_wallet_router)
    app.include_router(swaps_router)
    app.include_router(device_attestation_router)
    app.include_router(device_credentials_router)

    # WebSocket: latest market quotes (no auth in V1)
    @app.websocket("/ws/market-data")
    async def ws_market_data(websocket: WebSocket):
        await handle_market_data_ws(websocket)

    # ============================================================================
    # Health & Root
    # ============================================================================

    @app.get("/")
    def root():
        return {"ok": True, "service": "arquantix-api", "version": "2.0.0"}

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "arquantix-api"}

    @app.get("/api/health")
    def api_health():
        return {"ok": True}

    # Toujours renvoyer du JSON en 500 (évite "Unexpected token 'I'... is not valid JSON" côté client)
    import logging
    _log = logging.getLogger("arquantix.api")

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        _log.exception("Unhandled: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

    # Cron Refresh Data : toutes les minutes si active (backfill barres en retard)
    if not getattr(app.state, "testing", False):
        import threading
        import time
        def _cron_refresh_loop():
            from database import SessionLocal
            from services.market_data.routes import run_backfill_lag_logic
            from services.market_data.cron_refresh import (
                is_cron_enabled,
                CRON_INTERVAL_SECONDS,
                add_cron_log,
            )
            while True:
                time.sleep(CRON_INTERVAL_SECONDS)
                if not is_cron_enabled():
                    continue
                db = SessionLocal()
                try:
                    result = run_backfill_lag_logic(db)
                    add_cron_log(
                        "Refresh barres en retard",
                        result.get("download_summary") or [],
                    )
                except Exception as e:
                    _log.exception("Cron backfill-lag: %s", e)
                    add_cron_log("Refresh barres en retard (erreur)", [])
                finally:
                    db.close()
        _t = threading.Thread(target=_cron_refresh_loop, daemon=True)
        _t.start()
        _log.info("Cron Refresh Data started (interval=%ss)", 60)

        PURGE_M1_INTERVAL_SECONDS = 12 * 3600  # every 12 hours
        def _cron_purge_m1_loop():
            from database import SessionLocal
            from services.market_data.purge_m1_bars import run_purge_m1_bars
            from services.market_data.cron_refresh import add_cron_log
            while True:
                time.sleep(PURGE_M1_INTERVAL_SECONDS)
                db = SessionLocal()
                try:
                    deleted = run_purge_m1_bars(db)
                    add_cron_log("Purge M1 bars", [{"deleted": deleted}])
                except Exception as e:
                    _log.exception("Cron purge-m1: %s", e)
                    add_cron_log("Purge M1 bars (erreur)", [])
                finally:
                    db.close()
        _t2 = threading.Thread(target=_cron_purge_m1_loop, daemon=True)
        _t2.start()
        _log.info("Cron Purge M1 bars started (interval=%ss)", PURGE_M1_INTERVAL_SECONDS)

        _jti_cleanup_interval = int(os.getenv("AUTH_SPENT_JTI_CLEANUP_INTERVAL_SEC", "86400"))

        def _auth_spent_jti_cleanup_loop():
            from database import SessionLocal
            from services.auth.spent_jti_cleanup import run_spent_jti_cleanup

            while True:
                time.sleep(max(60, _jti_cleanup_interval))
                db = SessionLocal()
                try:
                    run_spent_jti_cleanup(db)
                except Exception as e:
                    _log.exception("Auth spent JTI cleanup failed: %s", e)
                finally:
                    db.close()

        _tj = threading.Thread(target=_auth_spent_jti_cleanup_loop, daemon=True)
        _tj.start()
        _log.info(
            "Auth spent JTI cleanup thread started (interval=%ss)",
            max(60, _jti_cleanup_interval),
        )

        _webauthn_ch_cleanup_interval = int(os.getenv("WEBAUTHN_CHALLENGE_CLEANUP_INTERVAL_SEC", "600"))

        def _webauthn_challenges_cleanup_loop():
            from database import SessionLocal
            from services.auth.webauthn_challenges_cleanup import (
                cleanup_expired_admin_email_otp_challenges,
                cleanup_expired_mobile_login_otp_challenges,
                cleanup_webauthn_challenges,
            )

            while True:
                time.sleep(max(60, _webauthn_ch_cleanup_interval))
                db = SessionLocal()
                try:
                    cleanup_webauthn_challenges(db)
                    cleanup_expired_admin_email_otp_challenges(db)
                    cleanup_expired_mobile_login_otp_challenges(db)
                except Exception as e:
                    _log.exception("WebAuthn challenges cleanup failed: %s", e)
                finally:
                    db.close()

        _tw = threading.Thread(target=_webauthn_challenges_cleanup_loop, daemon=True)
        _tw.start()
        _log.info(
            "WebAuthn challenges cleanup thread started (interval=%ss)",
            max(60, _webauthn_ch_cleanup_interval),
        )

        _auth_sec_retention_interval = int(os.getenv("AUTH_SECURITY_EVENTS_PURGE_INTERVAL_SEC", "86400"))

        def _auth_security_events_retention_loop():
            from database import SessionLocal
            from services.security.security_events_retention import purge_old_auth_security_events

            while True:
                time.sleep(max(60, _auth_sec_retention_interval))
                db = SessionLocal()
                try:
                    purge_old_auth_security_events(db)
                except Exception as e:
                    _log.exception("Auth security events retention purge failed: %s", e)
                finally:
                    db.close()

        _tsiem = threading.Thread(target=_auth_security_events_retention_loop, daemon=True)
        _tsiem.start()
        _log.info(
            "Auth security events retention purge thread started (interval=%ss)",
            max(60, _auth_sec_retention_interval),
        )

        def _init_price_alert_engine():
            from database import SessionLocal
            from services.redis_client import get_redis
            from services.price_alerts.engine import init_alert_engine
            from services.price_alerts.cache import load_all_active_alerts
            from services.notifications.dispatcher import init_dispatcher

            init_dispatcher(SessionLocal)

            r = get_redis()
            engine = init_alert_engine(r)
            if engine is None:
                return
            db = SessionLocal()
            try:
                load_all_active_alerts(r, db)
            except Exception as e:
                _log.exception("Failed to load price alerts into Redis: %s", e)
            finally:
                db.close()
        _t3 = threading.Thread(target=_init_price_alert_engine, daemon=True)
        _t3.start()

    if not testing:
        from services.security.two_factor_config_guard import (
            TwoFactorConfigGuardError,
            run_two_factor_config_guard,
        )

        try:
            run_two_factor_config_guard()
        except TwoFactorConfigGuardError as exc:
            import logging

            logging.getLogger("arquantix.api").critical("2FA config guard failed: %s", exc)
            raise

    return app


app = create_app()


# ============================================================================
# Auth
# ============================================================================

@app.post("/auth/login", response_model=Token)
def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    x_device_attestation: Optional[str] = Header(None, alias="X-Device-Attestation"),
):
    """Login — access + refresh JWT ; session persistée (Phase 2) + device binding via ``X-Device-ID``."""
    return perform_login(
        db=db,
        request=request,
        email=str(credentials.email),
        password=credentials.password,
        device_header=x_device_id,
        attest_header=x_device_attestation,
    )


@app.post("/auth/refresh", response_model=Token)
def auth_refresh(
    body: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    x_device_attestation: Optional[str] = Header(None, alias="X-Device-Attestation"),
):
    """Rotation stricte du refresh : session DB + denylist jti ; ``X-Device-ID`` aligné sur le jeton."""
    return perform_refresh(
        db=db,
        request=request,
        refresh_token=body.refresh_token,
        device_header=x_device_id,
        attest_header=x_device_attestation,
    )


@app.post("/auth/revoke", status_code=status.HTTP_204_NO_CONTENT)
def auth_revoke(
    request: Request,
    body: RevokeTokenRequest,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """Révoque la session liée au refresh — appareil effectif = en-tête ou claims JWT (``did`` / ``device_id``), comme ``/auth/refresh``."""
    perform_revoke(
        db=db,
        request=request,
        refresh_token=body.refresh_token,
        device_header=x_device_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/auth/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
def auth_revoke_all(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("session_revoke_all")),
    token: str = Depends(oauth2_scheme),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """Révoque toutes les sessions refresh de l’utilisateur (Bearer access)."""
    if not getattr(request.app.state, "testing", False):
        enforce_zero_trust_or_raise(
            db=db,
            request=request,
            user=current_user,
            token=token,
            action="auth.revoke_all",
            resource=f"user:{current_user.id}",
            x_device_id=x_device_id,
        )
    perform_revoke_all(db=db, request=request, user=current_user)
    dev = (x_device_id or "")[:128]
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="session_revoke_all",
        request=request,
        db=db,
        device_id=dev,
        extra={"endpoint": "POST /auth/revoke-all"},
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/auth/sessions", response_model=List[AuthSessionItem])
def auth_list_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
):
    """Sessions actives (non révoquées, non expirées) pour l’utilisateur courant."""
    rows = list_active_sessions(db=db, user=current_user)
    dev = (request.headers.get("x-device-id") or "")[:128]
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="view_sensitive_data",
        request=request,
        db=db,
        device_id=dev,
        extra={"endpoint": "GET /auth/sessions", "read_only": True},
    )
    db.commit()
    return rows


# ============================================================================
# Public Endpoints (Site Vitrine)
# ============================================================================

@app.get("/public/global", response_model=GlobalSettingsResponse)
def get_global_public(db: Session = Depends(get_db)):
    """Get global settings (public)"""
    global_settings = db.query(GlobalSettings).first()
    if not global_settings:
        # Return defaults if not set
        return GlobalSettingsResponse(
            id=0,
            site_name="Arquantix",
            tagline="Innovation Technology",
            socials_json={},
            seo_json={},
            updated_at=datetime.utcnow()
        )
    return global_settings


@app.get("/public/pages/{locale}/{slug}", response_model=PageResponse)
def get_page_public(locale: str, slug: str, db: Session = Depends(get_db)):
    """Get a published page by locale and slug (public)"""
    page = db.query(Page).filter(
        and_(
            Page.slug == slug,
            Page.locale == locale,
            Page.status == StatusEnum.PUBLISHED
        )
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@app.get(
    "/public/news/{locale}",
    response_model=List[NewsResponse],
    deprecated=True,
    summary="[DEPRECATED] Use Web /api/blog instead",
)
def get_news_list_public(locale: str, limit: int = 10, db: Session = Depends(get_db)):
    """Get published news list by locale (public). DEPRECATED: blog = Prisma Article sur la base unifiée, pas News (legacy quant)."""
    news = db.query(News).filter(
        and_(
            News.locale == locale,
            News.status == StatusEnum.PUBLISHED
        )
    ).order_by(News.published_at.desc()).limit(limit).all()
    return news


@app.get(
    "/public/news/{locale}/{slug}",
    response_model=NewsResponse,
    deprecated=True,
    summary="[DEPRECATED] Use Web /blog/[slug] instead",
)
def get_news_public(locale: str, slug: str, db: Session = Depends(get_db)):
    """Get a published news item by locale and slug (public). DEPRECATED: Blog uses Article model in Web."""
    news = db.query(News).filter(
        and_(
            News.slug == slug,
            News.locale == locale,
            News.status == StatusEnum.PUBLISHED
        )
    ).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news


@app.post("/public/contact", response_model=ContactSubmissionResponse, status_code=status.HTTP_201_CREATED)
def create_contact_submission(
    submission: ContactSubmissionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a contact submission (public)"""
    if crypto_feature_contact_enabled() and not is_encryption_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "CRYPTO_MISCONFIGURED",
                "message": "APPLICATION_ENCRYPT_CONTACT_SUBMISSIONS requires CRYPTO_LOCAL_MASTER_KEY_B64 or KMS.",
            },
        )
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    db_submission = ContactSubmission(ip=ip, user_agent=user_agent)
    encrypt_and_assign_contact_fields(
        db_submission,
        name=submission.name,
        email=str(submission.email),
        message=submission.message,
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    if crypto_feature_contact_enabled() and strip_plaintext_after_encrypt_contact():
        payload = contact_row_to_public_response_dict(
            db_submission,
            submitted_name=submission.name,
            submitted_email=str(submission.email),
            submitted_message=submission.message,
        )
        return ContactSubmissionResponse(**payload)
    return db_submission


# ============================================================================
# Admin Endpoints (Protected)
# ============================================================================

@app.get("/admin/global", response_model=GlobalSettingsResponse)
def get_global_admin(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get global settings (admin)"""
    global_settings = db.query(GlobalSettings).first()
    if not global_settings:
        # Create default if not exists
        global_settings = GlobalSettings(
            site_name="Arquantix",
            tagline="Innovation Technology",
            socials_json={},
            seo_json={}
        )
        db.add(global_settings)
        db.commit()
        db.refresh(global_settings)
    return global_settings


@app.put("/admin/global", response_model=GlobalSettingsResponse)
def update_global_admin(
    update: GlobalSettingsUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update global settings (admin)"""
    global_settings = db.query(GlobalSettings).first()
    if not global_settings:
        global_settings = GlobalSettings()
        db.add(global_settings)
    
    if update.site_name is not None:
        global_settings.site_name = update.site_name
    if update.tagline is not None:
        global_settings.tagline = update.tagline
    if update.socials_json is not None:
        global_settings.socials_json = update.socials_json
    if update.seo_json is not None:
        global_settings.seo_json = update.seo_json
    
    db.commit()
    db.refresh(global_settings)
    return global_settings


@app.get("/admin/pages")
def list_pages_admin(
    locale: Optional[str] = None,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all pages (admin) - React Admin format: {data: [...], total: n}"""
    query = db.query(Page)
    if locale:
        query = query.filter(Page.locale == locale)
    pages = query.order_by(Page.updated_at.desc()).all()
    # Convert to dict format for React Admin
    pages_data = [
        {
            "id": p.id,
            "slug": p.slug,
            "locale": p.locale,
            "title": p.title,
            "sections_json": p.sections_json or {},
            "seo_json": p.seo_json or {},
            "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "source_page_id": p.source_page_id,
            "translation_status": p.translation_status,
            "translation_meta_json": p.translation_meta_json,
        }
        for p in pages
    ]
    return {
        "data": pages_data,
        "total": len(pages_data)
    }


@app.post("/admin/pages", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
def create_page_admin(
    page: PageCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a page (admin)"""
    # Check if page with same slug+locale exists
    existing = db.query(Page).filter(
        and_(Page.slug == page.slug, Page.locale == page.locale)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Page with this slug and locale already exists")
    
    db_page = Page(**page.dict())
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    return db_page


@app.get("/admin/pages/{page_id}", response_model=PageResponse)
def get_page_admin(
    page_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a page by ID (admin)"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@app.put("/admin/pages/{page_id}", response_model=PageResponse)
def update_page_admin(
    page_id: int,
    update: PageUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a page (admin)"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    update_dict = update.dict(exclude_unset=True)
    if "status" in update_dict:
        update_dict["status"] = StatusEnum(update_dict["status"])
    if update_dict.get("status") == StatusEnum.PUBLISHED and not page.published_at:
        update_dict["published_at"] = datetime.utcnow()
    
    for key, value in update_dict.items():
        setattr(page, key, value)
    
    db.commit()
    db.refresh(page)
    return page


@app.delete("/admin/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page_admin(
    page_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a page (admin)"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    db.delete(page)
    db.commit()
    return None


@app.get("/admin/news", deprecated=True, summary="[DEPRECATED] Use Web admin articles instead")
def list_news_admin(
    locale: Optional[str] = None,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all news (admin) - React Admin format: {data: [...], total: n}"""
    query = db.query(News)
    if locale:
        query = query.filter(News.locale == locale)
    news_list = query.order_by(News.updated_at.desc()).all()
    # Convert to dict format for React Admin
    news_data = [
        {
            "id": n.id,
            "slug": n.slug,
            "locale": n.locale,
            "title": n.title,
            "excerpt": n.excerpt,
            "content_markdown": n.content_markdown,
            "cover_image_url": n.cover_image_url,
            "status": n.status.value if hasattr(n.status, 'value') else str(n.status),
            "published_at": n.published_at.isoformat() if n.published_at else None,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        }
        for n in news_list
    ]
    return {
        "data": news_data,
        "total": len(news_data)
    }


@app.post("/admin/news", response_model=NewsResponse, status_code=status.HTTP_201_CREATED, deprecated=True)
def create_news_admin(
    news: NewsCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a news item (admin)"""
    existing = db.query(News).filter(
        and_(News.slug == news.slug, News.locale == news.locale)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="News with this slug and locale already exists")
    
    db_news = News(**news.dict())
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return db_news


@app.get("/admin/news/{news_id}", response_model=NewsResponse, deprecated=True)
def get_news_admin(
    news_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a news item by ID (admin)"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news


@app.put("/admin/news/{news_id}", response_model=NewsResponse, deprecated=True)
def update_news_admin(
    news_id: int,
    update: NewsUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a news item (admin)"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    
    update_dict = update.dict(exclude_unset=True)
    if "status" in update_dict:
        update_dict["status"] = StatusEnum(update_dict["status"])
    if update_dict.get("status") == StatusEnum.PUBLISHED and not news.published_at:
        update_dict["published_at"] = datetime.utcnow()
    
    for key, value in update_dict.items():
        setattr(news, key, value)
    
    db.commit()
    db.refresh(news)
    return news


@app.delete("/admin/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT, deprecated=True)
def delete_news_admin(
    news_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a news item (admin)"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    db.delete(news)
    db.commit()
    return None


@app.get("/admin/contact-submissions")
def list_contact_submissions_admin(
    request: Request,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """List all contact submissions (admin) - React Admin format: {data: [...], total: n}"""
    zt_ctx = build_request_security_context(
        db=db,
        request=request,
        user=current_user,
        access_token=token,
        device_header=x_device_id,
    )
    submissions = db.query(ContactSubmission).order_by(ContactSubmission.created_at.desc()).all()
    submissions_data = [contact_row_to_admin_dict(s, security_context=zt_ctx) for s in submissions]
    return {
        "data": submissions_data,
        "total": len(submissions_data)
    }


# ============================================================================
# Media Upload (Admin)
# ============================================================================

@app.post("/admin/uploads")
async def upload_file(
    file: UploadFile = File(...),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Upload a file (admin only)
    Returns: { url: "http://..." }
    """
    if STORAGE_BACKEND != "local":
        raise HTTPException(status_code=501, detail="Only local storage is supported in MVP")
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix if file.filename else ".bin"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOADS_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Return URL
    file_url = f"{MEDIA_BASE_URL}/media/{unique_filename}"
    return {"url": file_url, "filename": unique_filename}


# ============================================================================
# Translation Endpoints (Admin)
# ============================================================================

class TranslateRequest(BaseModel):
    target_locale: str


@app.post("/admin/pages/{page_id}/translate")
def translate_page(
    page_id: int,
    request: TranslateRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Translate a page to target locale using OpenAI.
    Creates or updates the translated page.
    """
    # Get source page
    source_page = db.query(Page).filter(Page.id == page_id).first()
    if not source_page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not set")
    
    # Convert source page to dict
    source_dict = {
        "id": source_page.id,
        "slug": source_page.slug,
        "locale": source_page.locale,
        "title": source_page.title,
        "sections_json": source_page.sections_json or {},
        "seo_json": source_page.seo_json or {},
        "status": source_page.status.value if hasattr(source_page.status, 'value') else str(source_page.status),
    }
    
    # Translate
    try:
        translated_payload = translate_page_payload(source_dict, request.target_locale)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Check if translated page already exists
    existing_page = db.query(Page).filter(
        and_(
            Page.slug == source_page.slug,
            Page.locale == request.target_locale
        )
    ).first()
    
    action = "updated"
    if existing_page:
        # Update existing page
        existing_page.title = translated_payload["title"]
        existing_page.sections_json = translated_payload["sections_json"]
        existing_page.seo_json = translated_payload["seo_json"]
        existing_page.source_page_id = source_page.id
        existing_page.translation_status = "auto"
        existing_page.translation_meta_json = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "created_at": datetime.utcnow().isoformat(),
            "from": source_page.locale,
            "to": request.target_locale,
        }
        translated_page = existing_page
    else:
        # Create new page
        translated_page = Page(
            slug=translated_payload["slug"],
            locale=translated_payload["locale"],
            title=translated_payload["title"],
            sections_json=translated_payload["sections_json"],
            seo_json=translated_payload["seo_json"],
            status=StatusEnum(translated_payload["status"]),
            source_page_id=source_page.id,
            translation_status="auto",
            translation_meta_json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "created_at": datetime.utcnow().isoformat(),
                "from": source_page.locale,
                "to": request.target_locale,
            }
        )
        db.add(translated_page)
        action = "created"
    
    db.commit()
    db.refresh(translated_page)
    
    return {
        "ok": True,
        "translated_page_id": translated_page.id,
        "action": action
    }


@app.patch("/admin/pages/{page_id}/mark-reviewed")
def mark_page_reviewed(
    page_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a page translation as reviewed (admin)"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    page.translation_status = "reviewed"
    db.commit()
    db.refresh(page)
    return page


# Startup: Log all /api/ai/ routes
@app.on_event("startup")
async def startup_event():
    if getattr(app.state, "testing", False):
        return
    try:
        from database import DATABASE_URL as _db_url
        from db_connection_info import log_api_database_at_startup
        from env_docker_guard import log_docker_env_validation

        log_docker_env_validation()
        log_api_database_at_startup(_db_url)
    except Exception as exc:
        print(f"[API DB] WARNING: could not log database target: {exc}")
    print("\n" + "=" * 60)
    print("FastAPI Startup: Registered /api/ai/ routes:")
    print("=" * 60)
    for route in app.routes:
        if hasattr(route, "path") and "/api/ai/" in route.path:
            methods = getattr(route, "methods", set())
            methods_str = ", ".join(sorted(methods)) if methods else "N/A"
            print(f"  {methods_str:20} {route.path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
