"""Catalogue canonique des Action CTAs — Phase 2b.

Source de vérité unique pour tous les deep-links que les agents
peuvent injecter dans des `AssistanceChoiceOption`. C'est la
**whitelist** mentionnée dans `COMPLIANCE_TOPICS.md` § 8ter (sécurité
defense-in-depth).

──────────────────────────────────────────────────────────────────────
Garanties
──────────────────────────────────────────────────────────────────────

  - Toute génération de deep-link **doit** passer par `build_action()`
    qui ne peut produire qu'un kind inscrit ici. Impossible pour le
    LLM de forger un URL libre.
  - La whitelist est **synchronisée** côté Flutter avec
    `lib/features/search/application/assistance_deep_link_resolver.dart`
    (manuellement pour Phase 2b ; à dériver d'un schéma partagé en
    Phase 3+).
  - Les `kind` non encore disponibles côté mobile (cf.
    `available_phase_2b=False`) sont gardés ici pour la roadmap mais
    **rejetés** par `build_action` qui retourne `None`. Ainsi un agent
    peut conceptuellement proposer "uploader un doc" mais le deep-link
    ne sera jamais émis tant que l'écran Flutter n'existe pas.

Cf. `docs/arquantix/COMPLIANCE_TOPICS.md` § 4 (catalogue) et § 8ter
(sécurité whitelist).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Kinds canoniques (alignés avec COMPLIANCE_TOPICS.md § 4)
# ─────────────────────────────────────────────────────────────────────────


ActionKind = Literal[
    # Registration / KYC
    "resume_registration",
    # Dépôts (3 méthodes + générique)
    "deposit_funds",       # modal de choix
    "deposit_virement",
    "deposit_carte",
    "deposit_crypto",
    # Wallet / IBAN
    "view_wallet_euro",
    "view_iban",
    # Transactions
    "view_transactions",
    "view_transaction_detail",
    "download_transaction_statement",  # Phase 2c.2 — relevé PDF
    # Instruments (Phase 2c.6 — carte instrument_detail_card)
    "buy_instrument",
    "sell_instrument",
    "view_instrument",  # Phase 2c.7 — top_movers_crypto rows
    # Crypto Bundles (Phase 2 wiki — carte crypto_bundles_card)
    "view_bundle_detail",
    "invest_bundle",
    # Liste marchés crypto (entrée depuis agent action / swap guidance)
    "markets_crypto",
    # Articles / News (Phase 2c.7 — featured_articles_list)
    "open_article",
    # Profil
    "view_account_info",
    "view_security",
    # Phase 2c (déférés)
    "upload_document",
    "contact_support",
]


@dataclass(frozen=True)
class ActionSpec:
    """Spec immuable d'une action canonique."""

    kind: str
    default_label: str
    deep_link_template: str  # peut contenir un placeholder `{id}` etc.
    available_phase_2b: bool
    requires_param: Optional[str] = None  # ex: "transaction_id"


# Source de vérité — ordre logique d'apparition dans la doc.
_CATALOG: dict[str, ActionSpec] = {
    "resume_registration": ActionSpec(
        kind="resume_registration",
        default_label="Reprendre l'inscription",
        deep_link_template="vancelian://app/registration_resume",
        available_phase_2b=True,
    ),
    "deposit_funds": ActionSpec(
        kind="deposit_funds",
        default_label="Effectuer un dépôt",
        deep_link_template="vancelian://app/deposit",
        available_phase_2b=True,
    ),
    "deposit_virement": ActionSpec(
        kind="deposit_virement",
        default_label="Faire un virement",
        deep_link_template="vancelian://app/deposit/virement",
        available_phase_2b=True,
    ),
    "deposit_carte": ActionSpec(
        kind="deposit_carte",
        default_label="Déposer par carte",
        deep_link_template="vancelian://app/deposit/carte",
        available_phase_2b=True,
    ),
    "deposit_crypto": ActionSpec(
        kind="deposit_crypto",
        default_label="Déposer en crypto",
        deep_link_template="vancelian://app/deposit/crypto",
        available_phase_2b=True,
    ),
    "view_wallet_euro": ActionSpec(
        kind="view_wallet_euro",
        default_label="Voir mon compte euro",
        deep_link_template="vancelian://app/wallet/euro",
        available_phase_2b=True,
    ),
    "view_iban": ActionSpec(
        kind="view_iban",
        default_label="Voir mon IBAN",
        deep_link_template="vancelian://app/wallet/iban",
        available_phase_2b=True,
    ),
    "view_transactions": ActionSpec(
        kind="view_transactions",
        default_label="Voir mes transactions",
        deep_link_template="vancelian://app/transactions",
        available_phase_2b=True,
    ),
    "view_transaction_detail": ActionSpec(
        kind="view_transaction_detail",
        default_label="Voir la transaction",
        deep_link_template="vancelian://app/transactions/{id}",
        available_phase_2b=True,
        requires_param="transaction_id",
    ),
    "download_transaction_statement": ActionSpec(
        kind="download_transaction_statement",
        default_label="Télécharger le relevé",
        deep_link_template="vancelian://app/transactions/{id}/statement",
        available_phase_2b=True,
        requires_param="transaction_id",
    ),
    # Phase 2c.6 — instrument_detail_card (carte chat).
    # Le placeholder `{id}` est rempli par `instrument_id` (int côté
    # `market_data_instruments`). Le resolver Flutter récupère ensuite
    # le `CryptoAssetItem` correspondant pour démarrer le BuyFlow.
    "buy_instrument": ActionSpec(
        kind="buy_instrument",
        default_label="Acheter",
        deep_link_template="vancelian://app/instrument/{id}/buy",
        available_phase_2b=True,
        requires_param="instrument_id",
    ),
    "sell_instrument": ActionSpec(
        kind="sell_instrument",
        default_label="Vendre",
        deep_link_template="vancelian://app/instrument/{id}/sell",
        available_phase_2b=True,
        requires_param="instrument_id",
    ),
    # Phase 2c.7 — `top_movers_crypto` rows. Ouvre la fiche instrument
    # dans le crypto detail screen ; pas de flow buy/sell direct.
    "view_instrument": ActionSpec(
        kind="view_instrument",
        default_label="Voir",
        deep_link_template="vancelian://app/instrument/{id}",
        available_phase_2b=True,
        requires_param="instrument_id",
    ),
    # Phase 2 wiki — `crypto_bundles_card`. Le placeholder `{id}` est
    # rempli avec le `product_id` (UUID) du `pe_product_definitions`.
    # Le resolver Flutter (`AssistanceDeepLinkResolver._resolveBundleSub`)
    # ouvre la fiche détail (tap card) ou démarre le `BundleInvestFlow`
    # (bouton « Investir »).
    "view_bundle_detail": ActionSpec(
        kind="view_bundle_detail",
        default_label="Voir le détail",
        deep_link_template="vancelian://app/bundle/{id}",
        available_phase_2b=True,
        requires_param="bundle_id",
    ),
    "invest_bundle": ActionSpec(
        kind="invest_bundle",
        default_label="Investir",
        deep_link_template="vancelian://app/bundle/{id}/invest",
        available_phase_2b=True,
        requires_param="bundle_id",
    ),
    "markets_crypto": ActionSpec(
        kind="markets_crypto",
        default_label="Voir les cryptos cotées",
        deep_link_template="vancelian://app/markets/crypto",
        available_phase_2b=True,
    ),
    # Phase 2c.7 — `featured_articles_list` rows. Le placeholder `{id}`
    # est rempli avec le **slug** de l'article (URL-safe) que le client
    # passe ensuite à `ArticleDetailScreen(slug:)`.
    "open_article": ActionSpec(
        kind="open_article",
        default_label="Lire l'article",
        deep_link_template="vancelian://app/article/{id}",
        available_phase_2b=True,
        requires_param="article_slug",
    ),
    "view_account_info": ActionSpec(
        kind="view_account_info",
        default_label="Mes informations",
        deep_link_template="vancelian://app/profile/account",
        available_phase_2b=True,
    ),
    "view_security": ActionSpec(
        kind="view_security",
        default_label="Sécurité de mon compte",
        deep_link_template="vancelian://app/profile/security",
        available_phase_2b=True,
    ),
    # Reportés Phase 2c
    "upload_document": ActionSpec(
        kind="upload_document",
        default_label="Uploader un document",
        deep_link_template="vancelian://app/profile/documents/upload",
        available_phase_2b=False,
    ),
    "contact_support": ActionSpec(
        kind="contact_support",
        default_label="Contacter le support",
        deep_link_template="vancelian://app/help/contact",
        available_phase_2b=False,
    ),
}


# ─────────────────────────────────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────────────────────────────────


def is_known_kind(kind: str) -> bool:
    """True si `kind` est dans le catalogue (peu importe disponibilité)."""
    return kind in _CATALOG


def is_available(kind: str) -> bool:
    """True si `kind` est disponible Phase 2b (écran Flutter ready)."""
    spec = _CATALOG.get(kind)
    return bool(spec and spec.available_phase_2b)


def get_spec(kind: str) -> Optional[ActionSpec]:
    """Spec immuable (ou None si kind inconnu)."""
    return _CATALOG.get(kind)


def catalog_entries_for_admin() -> list[dict[str, Any]]:
    """Lecture sérialisable pour espaces admin (whitelist CTA, ordre stable)."""

    rows: list[dict[str, Any]] = []
    for kind in sorted(_CATALOG.keys()):
        spec = _CATALOG[kind]
        rows.append(
            {
                "kind": spec.kind,
                "default_label": spec.default_label,
                "deep_link_template": spec.deep_link_template,
                "available_phase_2b": spec.available_phase_2b,
                "requires_param": spec.requires_param,
            }
        )
    return rows


def build_action(
    kind: str,
    *,
    label_override: Optional[str] = None,
    params: Optional[dict[str, str]] = None,
) -> Optional[dict[str, str]]:
    """Construit le dict {kind, label, deep_link} pour un Action CTA.

    Garanties :
      - Retourne `None` si `kind` inconnu OU non disponible Phase 2b
        (le caller doit gérer le fallback : pas de deep_link, juste
        du texte par exemple).
      - Si la spec a un `requires_param` mais `params` ne le contient
        pas, retourne `None` + log warning.
      - Le `deep_link_template` est résolu avec `params` (Python
        `str.format`). Pas d'injection possible : le template est
        statique, `params` ne peuvent que remplir des placeholders
        explicites.

    Args:
        kind: identifier canonique (cf. `ActionKind`).
        label_override: texte du bouton si différent du défaut.
        params: dict pour résoudre les placeholders du template
                (ex: `{"id": "abc-123"}` pour
                `view_transaction_detail`).

    Returns:
        Dict `{"kind", "label", "deep_link"}` prêt à être attaché à
        une `AssistanceChoiceOption`, ou `None`.
    """
    spec = _CATALOG.get(kind)
    if spec is None:
        logger.warning("action_cta_catalog.unknown_kind kind=%r", kind)
        return None
    if not spec.available_phase_2b:
        logger.info(
            "action_cta_catalog.deferred kind=%r (Phase 2c+)", kind
        )
        return None

    if spec.requires_param:
        if not params or spec.requires_param not in params:
            logger.warning(
                "action_cta_catalog.missing_param kind=%r required=%s",
                kind,
                spec.requires_param,
            )
            return None
        # On utilise `id` dans le template (URL convention) mais le
        # param d'entrée a un nom plus parlant.
        substitutions = {"id": params[spec.requires_param]}
    else:
        substitutions = {}

    try:
        deep_link = spec.deep_link_template.format(**substitutions)
    except (KeyError, IndexError) as exc:
        logger.warning(
            "action_cta_catalog.template_error kind=%r exc=%s", kind, exc
        )
        return None

    return {
        "kind": kind,
        "label": (label_override or spec.default_label)[:80].strip(),
        "deep_link": deep_link,
    }


def is_known_deep_link(deep_link: str) -> bool:
    """Validation defense-in-depth : reconnaît `deep_link` comme produit
    par notre catalogue (template match — accepte les placeholders
    résolus type `view_transaction_detail`).

    Utilisé côté SSE pour stripper toute option avec un `deep_link`
    forgé hors-catalogue.

    Garanties :
      - Rejette tout URL ne commençant pas par `vancelian://`.
      - Rejette les **templates non résolus** (présence de `{` ou `}`).
      - Pour les kinds avec placeholder, vérifie que le segment id est
        non-vide ET ne contient pas de slash supplémentaire.
    """
    if not deep_link or not deep_link.startswith("vancelian://"):
        return False
    # Templates non résolus : on refuse explicitement (le LLM ne doit
    # pas pouvoir injecter un URL contenant `{...}`).
    if "{" in deep_link or "}" in deep_link:
        return False
    for spec in _CATALOG.values():
        if not spec.available_phase_2b:
            continue
        template = spec.deep_link_template
        if "{" not in template:
            if deep_link == template:
                return True
            continue
        # Match avec placeholder `{id}` : on extrait la portion entre
        # prefix et suffix et on vérifie qu'elle n'a pas de `/` interne
        # (sinon c'est un sous-chemin non prévu).
        prefix, _, suffix = template.partition("{id}")
        if not deep_link.startswith(prefix):
            continue
        if suffix and not deep_link.endswith(suffix):
            continue
        # Extrait le segment id.
        end = len(deep_link) - len(suffix) if suffix else len(deep_link)
        id_segment = deep_link[len(prefix) : end]
        if not id_segment or "/" in id_segment:
            continue
        return True
    return False


__all__ = [
    "ActionKind",
    "ActionSpec",
    "build_action",
    "catalog_entries_for_admin",
    "get_spec",
    "is_available",
    "is_known_deep_link",
    "is_known_kind",
]
