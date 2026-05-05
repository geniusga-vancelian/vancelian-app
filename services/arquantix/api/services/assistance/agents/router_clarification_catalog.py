"""Catalogue **canonique** de clarifications par tag d'intention
(router v2 — Niveau 3.A : sujet identifié mais demande encore trop
générale).

Spec user 2026-05-04 :

  > « 3) sujet parfaitement identifié et ajusté aux différents sujets
  >   traité par le bot :
  >   A) mais la demande du client est encore trop générale : il faut
  >      demander des clarifications (liste des choses importantes à
  >      faire sur ce sujet -> à définir) »

──────────────────────────────────────────────────────────────────────
Stratégie hybride
──────────────────────────────────────────────────────────────────────

  1. **Si le tag détecté a un catalogue dédié** → on retourne le QCM
     canonique (prompt + 3-5 options calibrées éditorialement). Ces
     options sont **stables** (versionnées git), garantissent une
     expérience client cohérente, et peuvent être ajustées par PR.

  2. **Si le tag n'a pas de catalogue** ou si le LLM ne fournit pas de
     tag exploitable → fallback LLM (comportement Router v1) où le
     LLM rédige lui-même prompt + options.

──────────────────────────────────────────────────────────────────────
Convention par entrée
──────────────────────────────────────────────────────────────────────

```
"epargner": {
    "prompt"  : "...",                          # FR, ton chaleureux
    "options" : [
        ("agent_id", "Label client-friendly"),   # 3 à 5 entrées
        ...
    ],
}
```

  * ``agent_id`` ∈ ``{compliance, advisor, product, market}``.
  * 2 options peuvent partager le même ``agent_id`` (angles distincts).
  * Le label final visible côté Flutter passe par
    ``ChoiceOption(label=...)`` (cf. ``service._build_choices_payload``).

──────────────────────────────────────────────────────────────────────
Évolution
──────────────────────────────────────────────────────────────────────

À tenir aligné avec :
  * ``router_intent_tags.py`` — toute nouvelle entrée doit pointer sur
    un ``tag`` existant.
  * ``router_system.md`` règle 5.5 — exemples calibrés.
  * Pattern advisor-first (Lot 4) : si la question mêle plusieurs
    angles, ne pas demander de clarification → routage advisor.

Tests : ``tests/test_assistance_router_clarification_catalog_unit.py``.
"""

from __future__ import annotations

from typing import Optional, TypedDict


class ClarificationOption(TypedDict):
    """1 option du QCM ``ask_clarification``."""

    agent_id: str
    label: str


class ClarificationEntry(TypedDict):
    """1 entrée canonique pour un tag donné."""

    prompt: str
    options: list[ClarificationOption]


# ─────────────────────────────────────────────────────────────────────
# Catalogue (router v2 — version 1, 2026-05-04)
# ─────────────────────────────────────────────────────────────────────
#
# Couverture :
#   * Famille ÉPARGNE        : epargner, securiser_capital, livret_coffre,
#                              rendement, avenir_securite
#   * Famille INVESTIR       : investir, performance, retraite,
#                              bundle_crypto, exclusive_offer,
#                              instrument_cote, immobilier_long_terme
#   * Famille COMPTE_OPS     : compte_kyc, depot, retrait, virement_sepa,
#                              carte_visa, banque
#   * Famille MARCHÉS        : actu_marche, opinion_marche,
#                              cours_evolution, macro_inflation, trading
#   * Famille TRANSVERSE     : reussir, projet_vie, decouvrir,
#                              argent_general
#
# Famille HORS_SUJET non couverte (utilise `redirect_off_topic` + liste
# fixe d'options, cf. lot 1).

CLARIFICATION_BY_TAG: dict[str, ClarificationEntry] = {
    # ── ÉPARGNE ────────────────────────────────────────────────
    "epargner": {
        "prompt": (
            "L'épargne, c'est exactement le cœur de Vancelian. "
            "Tu veux qu'on creuse quoi ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Voir les Coffres d'épargne (Flexible / Avenir)"},
            {"agent_id": "advisor", "label": "Combien je peux mettre de côté chaque mois"},
            {"agent_id": "advisor", "label": "Une stratégie d'épargne adaptée à mon profil"},
        ],
    },
    "securiser_capital": {
        "prompt": (
            "Bien sécuriser ton capital, c'est un point clé. "
            "Tu préfères qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Les produits Vancelian les plus sécurisés"},
            {"agent_id": "advisor", "label": "Une allocation prudente pour mon profil"},
            {"agent_id": "advisor", "label": "Comment équilibrer sécurité et rendement"},
        ],
    },
    "livret_coffre": {
        "prompt": (
            "Les coffres Vancelian, c'est un bon point d'entrée. "
            "Tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Découvrir le Coffre Flexible"},
            {"agent_id": "product", "label": "Découvrir le Coffre Avenir"},
            {"agent_id": "advisor", "label": "Lequel des deux pour mon profil"},
        ],
    },
    "rendement": {
        "prompt": (
            "Le rendement, c'est un sujet central. "
            "Tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Les rendements de nos coffres d'épargne"},
            {"agent_id": "product", "label": "Les rendements de nos offres exclusives"},
            {"agent_id": "advisor", "label": "Quel rendement viser pour mon profil"},
        ],
    },
    "avenir_securite": {
        "prompt": (
            "Préparer ton avenir financier, c'est précisément ce qu'on "
            "fait ensemble ici. Sur quoi tu veux qu'on regarde en priorité ?"
        ),
        "options": [
            {"agent_id": "advisor", "label": "Une stratégie long terme adaptée à mon profil"},
            {"agent_id": "product", "label": "Les solutions Vancelian long terme"},
            {"agent_id": "advisor", "label": "Préparer un projet (retraite, achat, transmission)"},
        ],
    },
    # ── INVESTIR ───────────────────────────────────────────────
    "investir": {
        "prompt": (
            "Investir, c'est tout l'objet de Vancelian. "
            "Sur quoi tu veux qu'on regarde ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Découvrir nos produits d'investissement"},
            {"agent_id": "advisor", "label": "Une allocation adaptée à mon profil"},
            {"agent_id": "market",  "label": "L'état du marché en ce moment"},
        ],
    },
    "performance": {
        "prompt": (
            "La performance, c'est un sujet qu'on regarde de près. "
            "Sur quel angle on creuse ?"
        ),
        "options": [
            {"agent_id": "market",  "label": "Les performances de nos produits en ce moment"},
            {"agent_id": "product", "label": "Comparer les performances entre produits"},
            {"agent_id": "advisor", "label": "Une stratégie pour optimiser ma performance"},
        ],
    },
    "retraite": {
        "prompt": (
            "Bien préparer ta retraite, c'est tout à fait notre terrain. "
            "Tu veux qu'on regarde par quel bout ?"
        ),
        "options": [
            {"agent_id": "advisor", "label": "Combien dois-je épargner pour ma retraite"},
            {"agent_id": "product", "label": "Les solutions retraite chez Vancelian"},
            {"agent_id": "advisor", "label": "Une stratégie long terme pour la retraite"},
        ],
    },
    "bundle_crypto": {
        "prompt": (
            "Les Crypto Baskets (Bundles), c'est une porte d'entrée "
            "élégante. Tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Voir tous les bundles disponibles"},
            {"agent_id": "advisor", "label": "Adapter un bundle à mon profil"},
            {"agent_id": "market",  "label": "Comparer les performances des bundles"},
        ],
    },
    "exclusive_offer": {
        "prompt": (
            "Les Offres Exclusives, c'est notre gamme à plus haut "
            "rendement. Tu veux qu'on regarde laquelle ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Découvrir le Cloud Mining"},
            {"agent_id": "product", "label": "Voir les offres immobilières (Dubai, Bali, Niseko)"},
            {"agent_id": "advisor", "label": "Laquelle pour mon profil et mes objectifs"},
        ],
    },
    "instrument_cote": {
        "prompt": (
            "Les instruments cotés, c'est un large univers. "
            "Tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Voir le cours d'un instrument précis"},
            {"agent_id": "market",  "label": "Que penser du marché en ce moment"},
            {"agent_id": "advisor", "label": "Quel instrument pour mon profil"},
        ],
    },
    "immobilier_long_terme": {
        "prompt": (
            "L'immobilier patrimonial, c'est un beau sujet. "
            "On regarde quoi en priorité ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Les offres immobilières Vancelian"},
            {"agent_id": "advisor", "label": "Bâtir un patrimoine immo long terme"},
            {"agent_id": "advisor", "label": "Préparer une transmission"},
        ],
    },
    # ── COMPTE & OPS ───────────────────────────────────────────
    "compte_kyc": {
        "prompt": (
            "Sur ton compte, je peux t'aider directement. "
            "C'est plutôt sur quoi ?"
        ),
        "options": [
            {"agent_id": "compliance", "label": "Statut de mon KYC / vérification d'identité"},
            {"agent_id": "compliance", "label": "Un justificatif demandé"},
            {"agent_id": "compliance", "label": "Une opération bloquée"},
        ],
    },
    "depot": {
        "prompt": (
            "Sur tes dépôts, je suis là pour t'aider. "
            "C'est plutôt sur quoi ?"
        ),
        "options": [
            {"agent_id": "compliance", "label": "Un dépôt qui n'arrive pas"},
            {"agent_id": "compliance", "label": "Comment effectuer un nouveau dépôt"},
            {"agent_id": "compliance", "label": "Voir mes dépôts en attente"},
        ],
    },
    "retrait": {
        "prompt": (
            "Sur tes retraits, je peux t'orienter. "
            "C'est plutôt sur quoi ?"
        ),
        "options": [
            {"agent_id": "compliance", "label": "Comment effectuer un retrait"},
            {"agent_id": "compliance", "label": "Un retrait en attente"},
            {"agent_id": "compliance", "label": "Les délais et frais de retrait"},
        ],
    },
    "virement_sepa": {
        "prompt": (
            "Sur les virements SEPA, je peux t'aider. "
            "C'est plutôt quoi ?"
        ),
        "options": [
            {"agent_id": "compliance", "label": "Mon IBAN Vancelian"},
            {"agent_id": "compliance", "label": "Un virement entrant qui n'arrive pas"},
            {"agent_id": "compliance", "label": "Effectuer un virement sortant"},
        ],
    },
    "carte_visa": {
        "prompt": (
            "Sur la carte Visa Vancelian, je peux t'orienter. "
            "C'est plutôt quoi ?"
        ),
        "options": [
            {"agent_id": "product",    "label": "Comment obtenir la carte"},
            {"agent_id": "product",    "label": "Frais et conditions"},
            {"agent_id": "compliance", "label": "Activer ou bloquer ma carte"},
        ],
    },
    "banque": {
        "prompt": (
            "Sur les aspects bancaires de ton compte Vancelian, "
            "tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "compliance", "label": "Mon compte EUR et mon IBAN"},
            {"agent_id": "compliance", "label": "Mes dépôts et retraits"},
            {"agent_id": "product",    "label": "La carte Visa et ses conditions"},
        ],
    },
    # ── MARCHÉS & ANALYSES ─────────────────────────────────────
    "actu_marche": {
        "prompt": (
            "L'actualité des marchés, on suit ça de près. "
            "Tu veux te concentrer sur quoi ?"
        ),
        "options": [
            {"agent_id": "market",  "label": "L'actu crypto en ce moment"},
            {"agent_id": "market",  "label": "L'actu actions / indices"},
            {"agent_id": "market",  "label": "Le contexte macro (taux, inflation)"},
        ],
    },
    "opinion_marche": {
        "prompt": (
            "Sur les analyses de marché, je peux t'orienter. "
            "Tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "market",  "label": "Que penser du marché crypto en ce moment"},
            {"agent_id": "market",  "label": "Que penser des actions / indices"},
            {"agent_id": "advisor", "label": "Est-ce le bon moment pour mon profil"},
        ],
    },
    "cours_evolution": {
        "prompt": (
            "Pour suivre les cours et l'évolution des prix, "
            "tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Voir le widget d'un instrument précis"},
            {"agent_id": "market",  "label": "Tendance d'un secteur (crypto, actions)"},
            {"agent_id": "advisor", "label": "Que faire vu l'évolution récente"},
        ],
    },
    "macro_inflation": {
        "prompt": (
            "Sur le contexte macroéconomique, je peux t'éclairer. "
            "Tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "market",  "label": "Inflation et taux directeurs"},
            {"agent_id": "market",  "label": "Impact macro sur les marchés crypto / actions"},
            {"agent_id": "advisor", "label": "Comment ajuster mes placements"},
        ],
    },
    "volatilite": {
        "prompt": (
            "La volatilité, c'est un sujet à prendre au sérieux. "
            "Sur quel angle on regarde ?"
        ),
        "options": [
            {"agent_id": "market",  "label": "État de la volatilité en ce moment"},
            {"agent_id": "advisor", "label": "Comment me protéger d'un krach"},
            {"agent_id": "product", "label": "Les produits Vancelian les moins volatils"},
        ],
    },
    "trading": {
        "prompt": (
            "Le trading sur Vancelian, c'est l'achat-vente direct "
            "d'actifs. Tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Comment fonctionne le trading spot"},
            {"agent_id": "product", "label": "Frais et conditions de trading"},
            {"agent_id": "advisor", "label": "Trading vs bundles : quelle approche pour moi"},
        ],
    },
    # ── TRANSVERSE ─────────────────────────────────────────────
    "reussir": {
        "prompt": (
            "Réussir financièrement, c'est exactement notre métier. "
            "Tu veux qu'on regarde quoi ?"
        ),
        "options": [
            {"agent_id": "advisor", "label": "Une stratégie pour atteindre mes objectifs"},
            {"agent_id": "advisor", "label": "Combien et où placer pour bien démarrer"},
            {"agent_id": "product", "label": "Découvrir nos produits"},
        ],
    },
    "projet_vie": {
        "prompt": (
            "Préparer un projet, c'est exactement le rôle de Vancelian. "
            "Sur quel projet on regarde ?"
        ),
        "options": [
            {"agent_id": "advisor", "label": "Préparer un achat (immo, voiture, voyage)"},
            {"agent_id": "advisor", "label": "Préparer ma retraite"},
            {"agent_id": "advisor", "label": "Préparer la transmission de mon patrimoine"},
        ],
    },
    "decouvrir": {
        "prompt": (
            "Bienvenue chez Vancelian. Tu veux découvrir quoi ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Les Coffres d'épargne (Flexible / Avenir)"},
            {"agent_id": "product", "label": "Les Crypto Baskets et Offres Exclusives"},
            {"agent_id": "product", "label": "Le compte EUR + carte Visa"},
            {"agent_id": "advisor", "label": "Quels produits pour mon profil"},
        ],
    },
    "argent_general": {
        "prompt": (
            "L'argent, c'est précisément notre sujet ici. "
            "Par où on commence ?"
        ),
        "options": [
            {"agent_id": "product", "label": "Découvrir un produit Vancelian"},
            {"agent_id": "advisor", "label": "Conseils pour mes placements"},
            {"agent_id": "advisor", "label": "Préparer un projet financier"},
            {"agent_id": "market",  "label": "Comprendre les marchés en ce moment"},
        ],
    },
}


def get_clarification_for_tag(
    tag: Optional[str],
) -> Optional[ClarificationEntry]:
    """Retourne le prompt + options canoniques pour un tag, ou
    ``None`` si le tag n'est pas couvert par le catalogue."""
    if not tag:
        return None
    return CLARIFICATION_BY_TAG.get(tag)


__all__ = [
    "ClarificationEntry",
    "ClarificationOption",
    "CLARIFICATION_BY_TAG",
    "get_clarification_for_tag",
]
