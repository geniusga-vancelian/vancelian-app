"""Repository introspectif côté **compliance** — Phase 2a.

Frontière de filtrage tipping-off matérielle : ce module **ne retourne
jamais** :

  - `auth_global_risk_score.score` (entier brut)
  - `auth_global_risk_score.level` (`LOW`/`MEDIUM`/`HIGH`)
  - les `deny_reason` d'`auth_security_decisions`
  - les match watchlist (OFAC/PEP)

Il les **lit** pour décider, puis traduit en signaux **client-facing
safe** (booléens neutres + message générique). Cf.
`MULTI_AGENTS_RUNTIME.md` § 5.

Toutes les fonctions sont **sync** et **best-effort** :
  - en cas d'erreur DB, on log et on retourne la valeur par défaut
    `_DEFAULT_SAFE_SIGNALS` ;
  - aucune exception ne sort du repo.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

# Constante neutre Decimal — réutilisée par les agrégats stats.
_ZERO: Decimal = Decimal("0")

from database import (
    AdminUser,
    AuthGlobalRiskScore,
    Person,
)
from services.portfolio_engine.clients.models import Client as PeClients

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────


# Niveaux de risque qui déclenchent un signal `requires_doc_upload=True`
# sans révéler le niveau lui-même au caller.
_RISK_LEVELS_DEMANDING_DOC: frozenset[str] = frozenset({"HIGH"})
_RISK_LEVELS_DEMANDING_STEP_UP: frozenset[str] = frozenset({"MEDIUM", "HIGH"})

_DEFAULT_SAFE_SIGNALS: dict[str, Any] = {
    "requires_doc_upload": False,
    "requires_step_up": False,
    "client_facing_message": None,
}


_CLIENT_FACING_DOC_UPLOAD_MESSAGE = (
    "Pour finaliser cette opération, nous devons compléter ton dossier. "
    "Tu peux téléverser les documents demandés depuis ton espace personnel."
)


# ─────────────────────────────────────────────────────────────────────────
# Helpers internes (toutes les requêtes raw passent par ici)
# ─────────────────────────────────────────────────────────────────────────


def _coerce_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _resolve_user_id_from_client(
    db: Session, *, client_id: UUID
) -> Optional[int]:
    """Remonte client_id → person_id → admin_users.id (pour `auth_*`).

    Retourne `None` si la chaîne casse à n'importe quel niveau (le repo
    saura interpréter en signal neutre).
    """
    try:
        row = (
            db.query(AdminUser.id)
            .join(PeClients, PeClients.person_id == AdminUser.person_id)
            .filter(PeClients.id == client_id)
            .one_or_none()
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo._resolve_user_id_from_client failed client_id=%s",
            client_id,
        )
        return None
    if row is None:
        return None
    return int(row[0])


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────


def fetch_client_status_summary(
    db: Session, *, client_id: Any
) -> dict[str, Any]:
    """Retourne le statut public du client.

    Champs retournés (tous déjà visibles côté UI Flutter, donc safe) :
      - `client_status`   : ``"active"`` | ``"pending"`` | ``"inactive"``
      - `kyc_status`      : ``"approved"`` | ``"pending"`` | ``"rejected"`` | …
      - `account_state`   : ``"ACTIVE"`` | ``"PARTIAL"`` | ``"BLOCKED"`` | None
      - `login_frozen`    : bool

    Returns:
        Dict normalisé. Si client introuvable, tous les champs sont
        nullables/par défaut (pas d'exception).
    """
    cid = _coerce_uuid(client_id)
    out: dict[str, Any] = {
        "client_status": None,
        "kyc_status": None,
        "account_state": None,
        "login_frozen": None,
    }
    if cid is None:
        return out

    try:
        row = (
            db.query(
                PeClients.status,
                PeClients.kyc_status,
                Person.account_state,
                Person.login_frozen,
            )
            .outerjoin(Person, Person.id == PeClients.person_id)
            .filter(PeClients.id == cid)
            .one_or_none()
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_client_status_summary failed client_id=%s",
            cid,
        )
        return out

    if row is None:
        return out
    status, kyc_status, account_state, login_frozen = row
    out["client_status"] = status
    out["kyc_status"] = kyc_status
    out["account_state"] = account_state
    out["login_frozen"] = bool(login_frozen) if login_frozen is not None else None
    return out


def fetch_safe_signals(
    db: Session, *, client_id: Any
) -> dict[str, Any]:
    """Signaux **gated** anti-tipping-off pour ce client.

    On lit `auth_global_risk_score` (via la chaîne client → person →
    admin_users → user_id) puis on traduit le niveau interne en signaux
    bool neutres. Le caller (LLM) ne peut **jamais** déduire le niveau
    de risque réel.

    Returns:
        Dict avec uniquement :
          - `requires_doc_upload` (bool)
          - `requires_step_up`    (bool)
          - `client_facing_message` (str | None)

    Notes:
        Si la chaîne ne résout pas (orphelin, client en onboarding, etc.),
        on retourne `_DEFAULT_SAFE_SIGNALS` (False/False/None) — neutre.
    """
    cid = _coerce_uuid(client_id)
    if cid is None:
        return dict(_DEFAULT_SAFE_SIGNALS)

    user_id = _resolve_user_id_from_client(db, client_id=cid)
    if user_id is None:
        return dict(_DEFAULT_SAFE_SIGNALS)

    try:
        row = (
            db.query(AuthGlobalRiskScore.level)
            .filter(AuthGlobalRiskScore.user_id == user_id)
            .one_or_none()
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_safe_signals risk_score_lookup_failed user_id=%s",
            user_id,
        )
        return dict(_DEFAULT_SAFE_SIGNALS)

    if row is None:
        return dict(_DEFAULT_SAFE_SIGNALS)

    level = (row[0] or "").strip().upper()

    requires_doc_upload = level in _RISK_LEVELS_DEMANDING_DOC
    requires_step_up = level in _RISK_LEVELS_DEMANDING_STEP_UP

    if requires_doc_upload:
        message: Optional[str] = _CLIENT_FACING_DOC_UPLOAD_MESSAGE
    else:
        message = None

    return {
        "requires_doc_upload": bool(requires_doc_upload),
        "requires_step_up": bool(requires_step_up),
        "client_facing_message": message,
    }


def fetch_compliance_state_snapshot(
    db: Session, *, client_id: Any
) -> dict[str, Any]:
    """Agrégateur lu par `read_compliance_state`.

    Combine :
      - `fetch_client_status_summary` (public)
      - `fetch_safe_signals` (gated)

    Garantit l'absence de fuite : les deux sources sont conçues pour
    être safe.
    """
    return {
        "status": fetch_client_status_summary(db, client_id=client_id),
        "safe_signals": fetch_safe_signals(db, client_id=client_id),
    }


# ─────────────────────────────────────────────────────────────────────────
# Registration progress (introspectif, schema-driven)
# ─────────────────────────────────────────────────────────────────────────


def fetch_registration_progress(
    db: Session, *, person_id: Any
) -> dict[str, Any]:
    """Snapshot du parcours d'inscription (registration_sessions/steps).

    Structure de retour (toujours JSON-safe) :

        {
          "session_status": "in_progress" | "completed" | "abandoned" | None,
          "current_step_id": str | None,    # opaque côté client
          "completed_steps": int,
          "total_steps_recorded": int,      # nb de rows registration_session_steps
          "last_activity_at": ISO8601 str | None,
        }

    Ne retourne **aucun** détail sur les valeurs saisies (`registration_session_data.value_json`)
    pour ne pas inviter l'agent à raisonner sur des données KYC sensibles.

    Si pas de `person_id` ou pas de session : payload « vide » mais valide.
    """
    out: dict[str, Any] = {
        "session_status": None,
        "current_step_id": None,
        "completed_steps": 0,
        "total_steps_recorded": 0,
        "last_activity_at": None,
    }
    pid = _coerce_uuid(person_id)
    if pid is None:
        return out

    try:
        from database import RegistrationSession, RegistrationSessionStep
    except ImportError:
        return out

    try:
        sess = (
            db.query(
                RegistrationSession.id,
                RegistrationSession.status,
                RegistrationSession.current_step_id,
            )
            .filter(RegistrationSession.person_id == pid)
            .order_by(RegistrationSession.id.desc())
            .first()
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_registration_progress session_lookup failed person_id=%s",
            pid,
        )
        return out

    if sess is None:
        return out

    sess_id, status, current_step_id = sess
    out["session_status"] = status
    out["current_step_id"] = (
        str(current_step_id) if current_step_id is not None else None
    )

    try:
        rows = (
            db.query(
                RegistrationSessionStep.status,
                RegistrationSessionStep.completed_at,
            )
            .filter(RegistrationSessionStep.session_id == sess_id)
            .all()
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_registration_progress steps_lookup failed sess=%s",
            sess_id,
        )
        return out

    completed = 0
    last_at = None
    for r in rows:
        if r.status == "completed":
            completed += 1
        if r.completed_at is not None and (last_at is None or r.completed_at > last_at):
            last_at = r.completed_at

    out["completed_steps"] = completed
    out["total_steps_recorded"] = len(rows)
    out["last_activity_at"] = last_at.isoformat() if last_at else None
    return out


# ─────────────────────────────────────────────────────────────────────────
# Documents (introspectif, schema-driven, sans leak storage_*)
# ─────────────────────────────────────────────────────────────────────────


def fetch_documents_summary(
    db: Session, *, person_id: Any
) -> dict[str, Any]:
    """Résumé documents par `doc_type` × `status`.

    Ne retourne **jamais** :
      - `storage_bucket` / `storage_key` / `storage_provider` (URLs ops)
      - `metadata_json` (peut contenir des données AML internes)

    Structure :

        {
          "total_count": int,
          "by_type": {"id_proof": 1, "address_proof": 0, ...},
          "by_status": {"approved": 1, "pending_review": 0, ...},
          "latest_uploaded_at": ISO8601 str | None,
        }
    """
    out: dict[str, Any] = {
        "total_count": 0,
        "by_type": {},
        "by_status": {},
        "latest_uploaded_at": None,
    }
    pid = _coerce_uuid(person_id)
    if pid is None:
        return out

    try:
        from database import Document
    except ImportError:
        return out

    try:
        rows = (
            db.query(Document.doc_type, Document.status, Document.created_at)
            .filter(Document.person_id == pid)
            .all()
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_documents_summary failed person_id=%s",
            pid,
        )
        return out

    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    latest = None
    for r in rows:
        by_type[r.doc_type] = by_type.get(r.doc_type, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        if r.created_at is not None and (latest is None or r.created_at > latest):
            latest = r.created_at

    out["total_count"] = len(rows)
    out["by_type"] = by_type
    out["by_status"] = by_status
    out["latest_uploaded_at"] = latest.isoformat() if latest else None
    return out


# ─────────────────────────────────────────────────────────────────────────
# Transactions (introspectif sur pe_orders, schema-driven minimal)
# ─────────────────────────────────────────────────────────────────────────


def fetch_transactions_summary(
    db: Session, *, client_id: Any, limit: int = 25
) -> dict[str, Any]:
    """Résumé transactionnel client (Phase 2a + Phase 2b extension).

    Lit **deux** sources :
      1. ``pe_orders`` — ordres titres / investissement
      2. ``custody_transactions`` (via ``custody_accounts.client_id``)
         — mouvements cash : dépôts / retraits virements bancaires,
         carte, crypto, etc. **Source primaire** pour les questions
         *« où est mon dépôt ? »*.

    Ne charge aucun montant brut sensible : agrège par état + retourne
    les N dernières références opaques (UUID).

    Structure (rétro-compat Phase 2a — ``orders_count`` agrège les
    deux sources, ``by_status`` est mergé) :

        {
          "orders_count":      int,                      # somme orders + cash
          "by_status":         {"completed": 12, ...},
          "last_order_at":     ISO8601 str | None,
          "recent_order_ids":  [str, ...]  # max `limit` mixés
          # — Phase 2b : breakdown détaillé par source —
          "cash_movements_count":   int,
          "cash_by_kind":           {"deposit": 1, "withdrawal": 0, ...},
          "cash_by_status":         {"completed": 1, ...},
          "last_cash_movement_at":  ISO8601 | None,
          "investment_orders_count": int,
        }

    Robustesse : tout échec d'import ou de requête sur l'une des
    sources est best-effort — les autres restent disponibles. Jamais
    d'exception remontée.
    """
    out: dict[str, Any] = {
        "orders_count": 0,
        "by_status": {},
        "last_order_at": None,
        "recent_order_ids": [],
        # Phase 2b breakdown
        "cash_movements_count": 0,
        "cash_by_kind": {},
        "cash_by_status": {},
        "last_cash_movement_at": None,
        "investment_orders_count": 0,
    }
    cid = _coerce_uuid(client_id)
    if cid is None:
        return out

    by_status: dict[str, int] = {}
    latest = None
    ids: list[str] = []

    # ── Source 1 — pe_orders (titres / investissement) ────────────
    try:
        from services.portfolio_engine.orders.models import (
            Order as PeOrder,
        )

        order_rows = (
            db.query(PeOrder.id, PeOrder.status, PeOrder.created_at)
            .filter(PeOrder.client_id == cid)
            .order_by(PeOrder.created_at.desc())
            .limit(max(1, min(limit, 100)))
            .all()
        )
        for r in order_rows:
            by_status[r.status] = by_status.get(r.status, 0) + 1
            if r.created_at is not None and (
                latest is None or r.created_at > latest
            ):
                latest = r.created_at
            ids.append(str(r.id))
        out["investment_orders_count"] = len(order_rows)
    except ImportError:
        pass
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_transactions_summary pe_orders failed cid=%s",
            cid,
        )

    # ── Source 2 — custody_transactions (cash : dépôts/retraits) ──
    cash_by_kind: dict[str, int] = {}
    cash_by_status: dict[str, int] = {}
    cash_count = 0
    last_cash_at = None
    try:
        from sqlalchemy import text

        cash_rows = db.execute(
            text(
                """
                SELECT ct.id, ct.transaction_type, ct.transaction_kind,
                       ct.direction, ct.status, ct.created_at
                  FROM custody_transactions ct
                  JOIN custody_accounts ca ON ca.id = ct.account_id
                 WHERE ca.client_id = :cid
                 ORDER BY ct.created_at DESC
                 LIMIT :lim
                """
            ),
            {"cid": str(cid), "lim": max(1, min(limit, 100))},
        ).fetchall()
        for r in cash_rows:
            cash_count += 1
            tx_type = r.transaction_type or "unknown"
            cash_by_kind[tx_type] = cash_by_kind.get(tx_type, 0) + 1
            tx_status = r.status or "unknown"
            cash_by_status[tx_status] = cash_by_status.get(tx_status, 0) + 1
            # Aggregate dans by_status global (pour rétro-compat
            # Phase 2a : la classification cascade utilise by_status
            # pour détecter `failed/rejected`).
            by_status[tx_status] = by_status.get(tx_status, 0) + 1
            if r.created_at is not None:
                if latest is None or r.created_at > latest:
                    latest = r.created_at
                if last_cash_at is None or r.created_at > last_cash_at:
                    last_cash_at = r.created_at
            ids.append(str(r.id))
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_transactions_summary custody_tx failed cid=%s",
            cid,
        )

    # ── Merge ─────────────────────────────────────────────────────
    out["orders_count"] = out["investment_orders_count"] + cash_count
    out["by_status"] = by_status
    out["last_order_at"] = latest.isoformat() if latest else None
    # Conserve le tri global décroissant et tronque à `limit`.
    out["recent_order_ids"] = ids[: max(1, min(limit, 100))]
    out["cash_movements_count"] = cash_count
    out["cash_by_kind"] = cash_by_kind
    out["cash_by_status"] = cash_by_status
    out["last_cash_movement_at"] = (
        last_cash_at.isoformat() if last_cash_at else None
    )
    return out


def fetch_transaction_detail(
    db: Session, *, client_id: Any, transaction_id: Any
) -> dict[str, Any]:
    """Détail **safe** d'une transaction (Phase 2b).

    Cherche dans **deux sources** dans cet ordre :
      1. ``pe_orders`` — ordre d'investissement
      2. ``custody_transactions`` — mouvement cash (dépôt/retrait)

    Vérifie l'ownership : la `transaction_id` doit appartenir au
    `client_id` courant — sinon retourne `{"error": "not_found"}` (PAS
    `forbidden`, pour ne pas leak l'existence d'une transaction tierce).

    Structure (toujours JSON-safe, sans PII contrepartie) :

        {
          "transaction_id": str,           # echo de l'input
          "status":         str | None,    # ex. "completed", "pending"
          "kind":           str | None,    # ex. "deposit", "bank_transfer_in", "swap"
          "source":         str | None,    # "investment" | "cash"
          "created_at":     ISO8601 | None,
          "updated_at":     ISO8601 | None,
          "is_inbound":     bool | None,   # True si dépôt/entrée (credit)
          "amount":         Decimal | None,# Phase 2c.4 — exposé pour
                                           # composition serveur de
                                           # `summary` côté tool. Le
                                           # tool DOIT le strip avant
                                           # retour LLM (anti-tipping
                                           # off). Disponible uniquement
                                           # pour la source `cash`.
          "currency":       str | None,    # ex. "EUR" — idem `amount`.
        }

    Volontairement absent : contrepartie, IBAN bénéficiaire, etc.
    `amount` / `currency` sont exposés depuis Phase 2c.4 mais avec une
    contrainte stricte côté tool : ils sont consommés **uniquement**
    pour générer le récap textuel destiné à l'embed UI (rendu côté
    Flutter sur l'API user authentifiée — pas de leak au LLM).
    """
    out: dict[str, Any] = {
        "transaction_id": str(transaction_id) if transaction_id else None,
        "status": None,
        "kind": None,
        "source": None,
        "created_at": None,
        "updated_at": None,
        "is_inbound": None,
        "amount": None,
        "currency": None,
    }
    cid = _coerce_uuid(client_id)
    tid = _coerce_uuid(transaction_id)
    if cid is None or tid is None:
        return {**out, "error": "not_found"}

    # ── Source 1 — pe_orders ──────────────────────────────────────
    try:
        from services.portfolio_engine.orders.models import Order as PeOrder

        try:
            row = (
                db.query(PeOrder)
                .filter(PeOrder.id == tid, PeOrder.client_id == cid)
                .one_or_none()
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "compliance_repo.fetch_transaction_detail pe_orders failed "
                "cid=%s tid=%s",
                cid,
                tid,
            )
            row = None
        if row is not None:
            out["source"] = "investment"
            out["status"] = getattr(row, "status", None)
            kind = getattr(row, "order_kind", None) or getattr(row, "kind", None)
            out["kind"] = kind
            created_at = getattr(row, "created_at", None)
            updated_at = getattr(row, "updated_at", None)
            out["created_at"] = created_at.isoformat() if created_at else None
            out["updated_at"] = updated_at.isoformat() if updated_at else None
            if kind:
                out["is_inbound"] = kind.startswith("deposit") or kind.startswith(
                    "inbound"
                )
            return out
    except ImportError:
        pass

    # ── Source 2 — custody_transactions ──────────────────────────
    try:
        from sqlalchemy import text

        row = db.execute(
            text(
                """
                SELECT ct.id, ct.transaction_type, ct.transaction_kind,
                       ct.direction, ct.status, ct.created_at, ct.updated_at,
                       ct.amount, ct.currency
                  FROM custody_transactions ct
                  JOIN custody_accounts ca ON ca.id = ct.account_id
                 WHERE ct.id = :tid AND ca.client_id = :cid
                 LIMIT 1
                """
            ),
            {"tid": str(tid), "cid": str(cid)},
        ).first()
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_transaction_detail custody_tx failed "
            "cid=%s tid=%s",
            cid,
            tid,
        )
        return {**out, "error": "repo_unavailable"}

    if row is None:
        return {**out, "error": "not_found"}

    out["source"] = "cash"
    out["status"] = row.status
    # ``kind`` priorise `transaction_kind` (plus précis : bank_transfer_in,
    # card_in, crypto_in…) puis fallback `transaction_type` (deposit,
    # withdraw…).
    out["kind"] = row.transaction_kind or row.transaction_type
    out["created_at"] = row.created_at.isoformat() if row.created_at else None
    out["updated_at"] = row.updated_at.isoformat() if row.updated_at else None
    out["is_inbound"] = (row.direction or "").lower() == "credit"
    # Phase 2c.4 — `amount` / `currency` exposés pour composition du
    # `summary` côté tool. Doivent être strippés avant return au LLM.
    out["amount"] = row.amount
    out["currency"] = row.currency
    return out


# ─────────────────────────────────────────────────────────────────────────
# Transactions — listing détaillé filtrable (Phase 2c.3)
# ─────────────────────────────────────────────────────────────────────────


# Mapping `category` (LLM-friendly) → clauses SQL sur
# `custody_transactions`. Le LLM choisit une catégorie « métier »
# (« deposits », « withdrawals »…) plutôt que les valeurs internes
# (`bank_transfer_in`…). Toute valeur hors mapping → pas de filtre
# (équivalent `all`).
_CATEGORY_FILTERS: dict[str, dict[str, Any]] = {
    # Toutes les entrées (crédit) quelle que soit la méthode.
    "deposits": {"direction": "credit"},
    # Toutes les sorties (débit).
    "withdrawals": {"direction": "debit"},
    # Carte : entrée (alimentation par carte).
    "cards": {"transaction_kinds": ("card_in",)},
    # Crypto : entrée crypto (Phase 2b minimal — extensible).
    "crypto": {"transaction_kinds": ("crypto_in",)},
    # Virement bancaire (entrée OU sortie).
    "bank_transfer": {
        "transaction_kinds": ("bank_transfer_in", "bank_transfer_out"),
    },
    "all": {},
}


_ALLOWED_DIRECTIONS: frozenset[str] = frozenset({"credit", "debit"})
_ALLOWED_STATUSES: frozenset[str] = frozenset(
    {"pending", "completed", "failed", "rejected", "on_hold", "cancelled"}
)


def fetch_transactions_list(
    db: Session,
    *,
    client_id: Any,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Liste détaillée des transactions cash du client (Phase 2c.3).

    Lit ``custody_transactions`` joint à ``custody_accounts`` pour
    vérifier l'ownership. Source unique = cash (pas de pe_orders ici :
    ce listing sert au sub-agent ``compliance.transactional`` qui
    s'intéresse aux opérations de compte ; les ordres titres sont
    couverts ailleurs).

    Filtres (combinables, AND) :

      - ``category`` (LLM-friendly) : ``"deposits"`` (= credit),
        ``"withdrawals"`` (= debit), ``"cards"`` (kind=card_in),
        ``"crypto"`` (kind=crypto_in), ``"bank_transfer"`` (kinds
        bank_transfer_in/out), ``"all"`` (défaut).
      - ``direction`` : ``"credit"`` ou ``"debit"`` (override / combinable
        avec ``category``).
      - ``status`` : ``"pending"`` / ``"completed"`` / etc. — toute
        valeur hors enum est ignorée silencieusement.
      - ``since`` : ISO8601 date (ex. ``"2026-01-01"``) — filtre
        ``created_at >=``.
      - ``limit`` : 1..50 (clamp).

    Best-effort : tout échec retourne ``[]`` (jamais d'exception).

    Structure de chaque item retourné :

        {
          "id":               str (UUID),
          "transaction_type": str,
          "transaction_kind": str | None,
          "direction":        "credit" | "debit",
          "status":           str,
          "amount":           Decimal,    # montant absolu, signe via direction
          "currency":         str,        # ex. "EUR"
          "created_at":       datetime,
        }

    L'output est trié ``created_at`` décroissant (le plus récent
    d'abord — convention « historique récent »).
    """
    cid = _coerce_uuid(client_id)
    if cid is None:
        return []

    safe_limit = max(
        1, min(int(limit) if limit is not None else 20, 50)
    )

    # Construction des clauses dynamiques (paramétrées, pas de
    # f-string dans le SQL côté valeurs).
    where_parts: list[str] = ["ca.client_id = :cid"]
    params: dict[str, Any] = {"cid": str(cid), "lim": safe_limit}

    cat_filter = _CATEGORY_FILTERS.get((category or "").strip().lower())
    if cat_filter:
        if "direction" in cat_filter:
            where_parts.append("ct.direction = :cat_direction")
            params["cat_direction"] = cat_filter["direction"]
        if "transaction_kinds" in cat_filter:
            kinds = cat_filter["transaction_kinds"]
            placeholders = ", ".join(f":kind_{i}" for i in range(len(kinds)))
            where_parts.append(f"ct.transaction_kind IN ({placeholders})")
            for i, k in enumerate(kinds):
                params[f"kind_{i}"] = k

    dir_norm = (direction or "").strip().lower()
    if dir_norm in _ALLOWED_DIRECTIONS:
        where_parts.append("ct.direction = :direction")
        params["direction"] = dir_norm

    status_norm = (status or "").strip().lower()
    if status_norm in _ALLOWED_STATUSES:
        where_parts.append("ct.status = :status")
        params["status"] = status_norm

    if since:
        params["since"] = str(since).strip()
        where_parts.append("ct.created_at >= CAST(:since AS TIMESTAMPTZ)")

    sql = f"""
        SELECT ct.id,
               ct.transaction_type,
               ct.transaction_kind,
               ct.direction,
               ct.status,
               ct.amount,
               ct.currency,
               ct.created_at
          FROM custody_transactions ct
          JOIN custody_accounts ca ON ca.id = ct.account_id
         WHERE {" AND ".join(where_parts)}
         ORDER BY ct.created_at DESC
         LIMIT :lim
    """

    try:
        from sqlalchemy import text

        rows = db.execute(text(sql), params).fetchall()
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_transactions_list failed cid=%s "
            "category=%s direction=%s status=%s",
            cid,
            category,
            direction,
            status,
        )
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": str(r.id),
                "transaction_type": r.transaction_type,
                "transaction_kind": r.transaction_kind,
                "direction": r.direction,
                "status": r.status,
                "amount": r.amount,
                "currency": r.currency,
                "created_at": r.created_at,
            }
        )
    return out


# ─────────────────────────────────────────────────────────────────────────
# Transactions — agrégats stats (Phase 2c.5)
# ─────────────────────────────────────────────────────────────────────────


def _build_tx_where_clause(
    *,
    cid_str: str,
    category: Optional[str],
    direction: Optional[str],
    status: Optional[str],
    since: Optional[str],
) -> tuple[str, dict[str, Any]]:
    """Construit la clause WHERE + params pour les requêtes
    stats sur ``custody_transactions``.

    Centralisé pour garantir cohérence entre ``fetch_transactions_list``,
    ``fetch_transaction_counts`` et ``fetch_transaction_amounts``.
    """
    where_parts: list[str] = ["ca.client_id = :cid"]
    params: dict[str, Any] = {"cid": cid_str}

    cat_filter = _CATEGORY_FILTERS.get((category or "").strip().lower())
    if cat_filter:
        if "direction" in cat_filter:
            where_parts.append("ct.direction = :cat_direction")
            params["cat_direction"] = cat_filter["direction"]
        if "transaction_kinds" in cat_filter:
            kinds = cat_filter["transaction_kinds"]
            placeholders = ", ".join(f":kind_{i}" for i in range(len(kinds)))
            where_parts.append(f"ct.transaction_kind IN ({placeholders})")
            for i, k in enumerate(kinds):
                params[f"kind_{i}"] = k

    dir_norm = (direction or "").strip().lower()
    if dir_norm in _ALLOWED_DIRECTIONS:
        where_parts.append("ct.direction = :direction")
        params["direction"] = dir_norm

    status_norm = (status or "").strip().lower()
    if status_norm in _ALLOWED_STATUSES:
        where_parts.append("ct.status = :status")
        params["status"] = status_norm

    if since:
        params["since"] = str(since).strip()
        where_parts.append("ct.created_at >= CAST(:since AS TIMESTAMPTZ)")

    return " AND ".join(where_parts), params


# Dimensions valides pour le ``GROUP BY`` côté counts. Toute valeur
# hors mapping → ``direction`` (default : entrées vs sorties).
_COUNTS_GROUP_BY: dict[str, str] = {
    "direction": "ct.direction",
    "status": "ct.status",
    "kind": "COALESCE(ct.transaction_kind, ct.transaction_type)",
    "month": "to_char(date_trunc('month', ct.created_at), 'YYYY-MM')",
}


def fetch_transaction_counts(
    db: Session,
    *,
    client_id: Any,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    group_by: str = "direction",
) -> list[dict[str, Any]]:
    """Compte les transactions cash agrégées selon une dimension.

    Output : liste de dicts ``{label, count}`` triée par count desc.
    Aucun montant exposé. Best-effort : retourne ``[]`` en cas d'échec.
    """
    cid = _coerce_uuid(client_id)
    if cid is None:
        return []

    group_expr = _COUNTS_GROUP_BY.get(
        (group_by or "").strip().lower(), _COUNTS_GROUP_BY["direction"]
    )

    where_clause, params = _build_tx_where_clause(
        cid_str=str(cid),
        category=category,
        direction=direction,
        status=status,
        since=since,
    )

    sql = f"""
        SELECT {group_expr} AS dimension_label,
               COUNT(*)     AS cnt
          FROM custody_transactions ct
          JOIN custody_accounts ca ON ca.id = ct.account_id
         WHERE {where_clause}
         GROUP BY {group_expr}
         ORDER BY cnt DESC, dimension_label ASC
    """

    try:
        from sqlalchemy import text

        rows = db.execute(text(sql), params).fetchall()
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_transaction_counts failed cid=%s "
            "group_by=%s",
            cid,
            group_by,
        )
        return []

    return [
        {"label": r.dimension_label or "unknown", "count": int(r.cnt or 0)}
        for r in rows
    ]


def fetch_transaction_amounts(
    db: Session,
    *,
    client_id: Any,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
) -> dict[str, Any]:
    """Sommes des montants par direction (credit / debit) sur ``completed``.

    On filtre intentionnellement les transactions non finalisées (pending,
    failed, on_hold, cancelled, rejected) **par défaut** : un *« total
    déposé »* doit refléter la réalité du compte, pas les tentatives. Le
    filtre ``status`` peut explicitement override (ex.
    ``status='pending'`` pour voir le montant en attente).

    Output :

        {
          "currency":          str,           # devise dominante
          "deposits_total":    Decimal,       # somme credit
          "withdrawals_total": Decimal,       # somme debit
          "net":               Decimal,       # deposits − withdrawals
          "by_currency":       dict,          # ventilation si multi-devise
        }

    Best-effort : retourne un payload neutre en cas d'échec.
    """
    cid = _coerce_uuid(client_id)
    empty: dict[str, Any] = {
        "currency": "EUR",
        "deposits_total": _ZERO,
        "withdrawals_total": _ZERO,
        "net": _ZERO,
        "by_currency": {},
    }
    if cid is None:
        return empty

    # Si l'appelant n'a pas explicitement filtré par statut, on
    # restreint aux transactions « finalisées » pour que les totaux
    # aient du sens métier. Un filtre explicite passe outre.
    effective_status = status
    if not effective_status:
        # Astuce : on combine via la clause WHERE existante en injectant
        # un statut. Le caller peut surcharger.
        effective_status = "completed"

    where_clause, params = _build_tx_where_clause(
        cid_str=str(cid),
        category=category,
        direction=direction,
        status=effective_status,
        since=since,
    )

    sql = f"""
        SELECT ct.direction,
               COALESCE(ct.currency, 'EUR') AS currency,
               COALESCE(SUM(ct.amount), 0) AS total
          FROM custody_transactions ct
          JOIN custody_accounts ca ON ca.id = ct.account_id
         WHERE {where_clause}
         GROUP BY ct.direction, COALESCE(ct.currency, 'EUR')
    """

    try:
        from sqlalchemy import text

        rows = db.execute(text(sql), params).fetchall()
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_transaction_amounts failed cid=%s",
            cid,
        )
        return empty

    by_currency: dict[str, dict[str, Any]] = {}
    for r in rows:
        ccy = r.currency or "EUR"
        bucket = by_currency.setdefault(
            ccy,
            {"deposits": _ZERO, "withdrawals": _ZERO},
        )
        try:
            value = Decimal(str(r.total))
        except (InvalidOperation, TypeError):
            value = _ZERO
        if (r.direction or "").lower() == "credit":
            bucket["deposits"] += value
        else:
            bucket["withdrawals"] += value

    if not by_currency:
        return empty

    # Devise dominante = celle avec le volume agrégé (deposits +
    # withdrawals) le plus élevé. Stable pour les rapports même en
    # multi-devise.
    dominant = max(
        by_currency.items(),
        key=lambda kv: (kv[1]["deposits"] + kv[1]["withdrawals"]),
    )
    main_ccy, main_bucket = dominant
    deposits = main_bucket["deposits"]
    withdrawals = main_bucket["withdrawals"]
    return {
        "currency": main_ccy,
        "deposits_total": deposits,
        "withdrawals_total": withdrawals,
        "net": deposits - withdrawals,
        "by_currency": {
            ccy: {
                "deposits": b["deposits"],
                "withdrawals": b["withdrawals"],
                "net": b["deposits"] - b["withdrawals"],
            }
            for ccy, b in by_currency.items()
        },
    }


# ─────────────────────────────────────────────────────────────────────────
# Portfolio — performance & allocation (Phase 2c.5 — Lots 2 & 3)
# ─────────────────────────────────────────────────────────────────────────


def fetch_portfolio_performance(db: Session, *, client_id: Any) -> dict[str, Any]:
    """Performance globale du portefeuille client en EUR.

    Réutilise les helpers existants ``get_portfolio_breakdown`` (NAV
    fiat+crypto), ``get_pnl`` (realized/unrealized/total) et
    ``get_net_deposits`` (cash flows externes) pour composer un payload
    homogène consommé par ``stats_portfolio_performance``.

    Returns:
        ``{
            currency:           "EUR",
            current_value:      float,   # NAV total (fiat + crypto)
            net_deposits:       float,   # cumul dépôts − retraits
            realized_pnl:       float,
            unrealized_pnl:     float,
            total_pnl:          float,
            performance_pct:    float | None,  # total_pnl / net_deposits * 100
        }``

    Best-effort : retourne un payload neutre en cas d'erreur (jamais
    d'exception remontée au runtime).
    """
    cid = _coerce_uuid(client_id)
    empty = {
        "currency": "EUR",
        "current_value": 0.0,
        "net_deposits": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "total_pnl": 0.0,
        "performance_pct": None,
    }
    if cid is None:
        return empty

    try:
        from services.portfolio_engine.valuation import (
            get_net_deposits,
            get_pnl,
            get_portfolio_breakdown,
        )

        breakdown = get_portfolio_breakdown(db, cid) or {}
        pnl = get_pnl(db, cid) or {}
        net_deposits_dec = get_net_deposits(db, cid)
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_portfolio_performance failed cid=%s",
            cid,
        )
        return empty

    nav = float(breakdown.get("total_value") or 0.0)
    realized = float(pnl.get("realized_pnl") or 0.0)
    unrealized = float(pnl.get("unrealized_pnl") or 0.0)
    total_pnl = float(pnl.get("total_pnl") or (realized + unrealized))
    try:
        net_deposits = float(net_deposits_dec or 0.0)
    except Exception:  # noqa: BLE001
        net_deposits = 0.0

    # Performance % : ratio PnL total / capital net mis sur la table.
    # On ne calcule que si net_deposits > 0 (dénominateur sain).
    perf_pct: Optional[float] = None
    if net_deposits > 0:
        perf_pct = round(total_pnl / net_deposits * 100, 2)

    return {
        "currency": "EUR",
        "current_value": round(nav, 2),
        "net_deposits": round(net_deposits, 2),
        "realized_pnl": round(realized, 2),
        "unrealized_pnl": round(unrealized, 2),
        "total_pnl": round(total_pnl, 2),
        "performance_pct": perf_pct,
    }


def fetch_portfolio_allocation(db: Session, *, client_id: Any) -> dict[str, Any]:
    """Allocation macro du portefeuille client : fiat / crypto direct / bundles.

    Réutilise ``get_portfolio_breakdown`` qui maintient déjà
    l'invariant ``direct + bundles ≈ crypto_total``.

    Le tool ``stats_portfolio_allocation`` consomme ce payload pour
    composer l'embed ``portfolio_allocation_donut`` côté Flutter.

    Returns:
        ``{
            currency:    "EUR",
            total_value: float,
            slices: [
                {key, label, value, percentage},
                ...
            ]
        }``

    Les slices à valeur ``0`` sont **filtrées** pour éviter de
    polluer le donut (sinon une part bleue de 0 % apparaît dans la
    légende). Best-effort : payload vide en cas d'erreur.
    """
    cid = _coerce_uuid(client_id)
    empty = {
        "currency": "EUR",
        "total_value": 0.0,
        "slices": [],
    }
    if cid is None:
        return empty

    try:
        from services.portfolio_engine.valuation import get_portfolio_breakdown

        breakdown = get_portfolio_breakdown(db, cid) or {}
    except Exception:  # noqa: BLE001
        logger.exception(
            "compliance_repo.fetch_portfolio_allocation failed cid=%s",
            cid,
        )
        return empty

    total = float(breakdown.get("total_value") or 0.0)
    if total <= 0:
        return {**empty, "currency": "EUR"}

    raw_slices = [
        {
            "key": "fiat",
            "label": "Cash (EUR)",
            "value": float(breakdown.get("fiat") or 0.0),
            "percentage": float(breakdown.get("fiat_pct") or 0.0),
        },
        {
            "key": "crypto_direct",
            "label": "Crypto en direct",
            "value": float(breakdown.get("crypto_direct") or 0.0),
            "percentage": float(breakdown.get("crypto_direct_pct") or 0.0),
        },
        {
            "key": "bundles",
            "label": "Bundles",
            "value": float(breakdown.get("bundles") or 0.0),
            "percentage": float(breakdown.get("bundles_pct") or 0.0),
        },
    ]

    # Filtre des slices nulles (≤ 0,01 € de tolérance pour éviter les
    # rounding artifacts). Un donut avec une slice à 0 € ferait du
    # bruit visuel inutile.
    slices = [s for s in raw_slices if s["value"] > 0.01]

    return {
        "currency": "EUR",
        "total_value": round(total, 2),
        "slices": [
            {
                "key": s["key"],
                "label": s["label"],
                "value": round(s["value"], 2),
                "percentage": round(s["percentage"], 2),
            }
            for s in slices
        ],
    }


# ─────────────────────────────────────────────────────────────────────────
# External AML signals (provider abstrait — Phase 2a stub safe)
# ─────────────────────────────────────────────────────────────────────────


def fetch_external_aml_signals(
    db: Session, *, person_id: Any
) -> dict[str, Any]:
    """Signaux externes AML (KYC provider, watchlist screener, etc.).

    Phase 2a : le provider est un **mock** statique qui ne révèle rien
    (`unknown` / `approved`). Le contrat est stable pour quand on
    branchera Sumsub / Onfido en Phase 3 (cf. RUNTIME § 6).

    Structure (toujours safe — les `flags` sont des étiquettes
    NON-LEAK) :

        {
          "kyc_provider":          "mock",
          "kyc_status":            "unknown" | "approved" | "pending" | "rejected",
          "watchlist_status":      "approved" | "pending" | "unknown",
          "flags":                 [str, ...]    # ex. ["doc_quality_low"]
          "client_facing_message": str | None,
        }

    Aucun match watchlist explicite n'est retourné — le LLM ne reçoit
    que des signaux pré-cuits et neutres.
    """
    pid = _coerce_uuid(person_id)
    # Phase 2a : on ne lit aucune source externe. On retourne un
    # payload statique safe. Le reste du code (router, agent prompt)
    # peut déjà s'y appuyer sans surprise quand on branchera un vrai
    # adapter en Phase 2b/3.
    return {
        "kyc_provider": "mock",
        "kyc_status": "unknown" if pid is not None else "unknown",
        "watchlist_status": "approved",
        "flags": [],
        "client_facing_message": None,
    }
