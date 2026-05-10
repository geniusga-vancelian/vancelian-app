"""Registre central des tools par agent — Phase 2a + Phase 2b.

Cf. `MULTI_AGENTS_RUNTIME.md` § 2.4 (Phase 2a) et
`COMPLIANCE_TOPICS.md` § 3 (Phase 2b sub-agents).

Convention :

  - `TOOLS_BY_AGENT[agent_id]`  → liste des modules-tools (objets exposant
    `SPEC: ToolSpec` + `execute(...)`).
  - `tools_for(agent_id)`       → renvoie les modules ; le filtrage par
    autonomy_max est appliqué dans `runtime/agent_loop.py`.
  - `find(agent_id, name)`      → résolution `tool_name → module` pour
    dispatch O(1) côté runtime.

Tous les agents reçoivent **`ask_user_question`** (tool transverse, cf.
RUNTIME § 7).

──────────────────────────────────────────────────────────────────────
Phase 2b — sub-agents Compliance
──────────────────────────────────────────────────────────────────────

L'agent `compliance` (top-level) est appelé par le router. Au tour 0,
il appelle obligatoirement `diagnose_compliance_topic` qui retourne
le topic dominant. Le runtime bascule alors `ctx.agent_id` vers le
sub-agent correspondant (`compliance.<topic>`), recharge le prompt et
restreint le set de tools.

Architecture en arbre :

    compliance                          ← entry-point router top-level
    ├── compliance.registration         ← sub-agent KYC/onboarding
    ├── compliance.remediation          ← sub-agent doc/AML follow-up
    ├── compliance.transactional        ← sub-agent operations focus
    └── compliance.general              ← fallback (= contenu Phase 2a)
"""

from __future__ import annotations

from typing import Sequence

from services.assistance.agents.tools.compliance import (
    diagnose_compliance_topic,
    list_transactions,
    propose_resume_registration,
    read_compliance_state,
    read_documents,
    read_external_aml_signals,
    read_registration_progress,
    read_transaction_detail,
    read_transactions,
    stats_portfolio_allocation,
    stats_portfolio_performance,
    stats_transaction_amounts,
    stats_transaction_counts,
)
from services.assistance.agents.tools.contracts import ToolModule
from services.assistance.agents.tools.market import (
    show_featured_articles,
    show_top_movers,
)
from services.assistance.agents.tools.action import (
    bundle_invest_start,
    crypto_buy_start,
    crypto_investment_intent_confirm,
    crypto_investment_intent_resolve,
    crypto_investment_intent_start,
    crypto_sell_start,
    crypto_swap_start,
    deposit_present_channels,
)
from services.assistance.agents.tools.product import (
    read_wiki_page,
    select_wiki_pages,
    show_bundle_detail,
    show_crypto_bundles,
    show_instrument_card,
    show_invest_confirmation_draft,
    show_invest_source_accounts,
)
from services.assistance.agents.tools.shared import (
    ask_user_question,
    consult_specialist,
    handoff_to_agent,
)


# Sous-set commun à tous les sub-agents compliance (lecture safe).
#
# Lot 1 « Wiki shared » (2026-05-06) — `select_wiki_pages` +
# `read_wiki_page` sont **shared** : tous les sub-agents compliance
# en bénéficient pour fonder leurs réponses sur les FAQ canoniques
# (anti-hallucination + cohérence cross-agents). Le filtre audience
# (cf. `select_wiki_pages._filter_matches_by_audience` et
# `read_wiki_page` audience guard) interdit aux non-product de lire
# les fiches `audience: internal`.
_COMPLIANCE_BASE_TOOLS: list[ToolModule] = [
    read_compliance_state,
    read_registration_progress,
    read_documents,
    read_transactions,
    read_external_aml_signals,
    select_wiki_pages,
    read_wiki_page,
    ask_user_question,
]


# Mapping `agent_id -> liste de modules-tools`.
#
# Note importante :
#   - L'agent `compliance` (top-level) n'a accès qu'à
#     `diagnose_compliance_topic` + `ask_user_question` au tour 0.
#     Cela force la classification avant tout raisonnement.
#   - Les sub-agents `compliance.<topic>` reçoivent `_COMPLIANCE_BASE_TOOLS`
#     + leurs tools spécifiques. Ils n'ont **PAS** accès à
#     `diagnose_compliance_topic` (évite les boucles dispatcher).
#   - **Phase 2c** : seuls `compliance.remediation`, `compliance.registration`,
#     `compliance.general` ont accès à `handoff_to_agent` (pas
#     `compliance.transactional` qui est terminal côté chaîne).
#     `consult_specialist` est exposé aux sub-agents compliance qui
#     en bénéficient (transactional, general) et JAMAIS à `product`
#     lui-même (anti-récursion : `product` est specialist consulté,
#     pas consulteur).
TOOLS_BY_AGENT: dict[str, list[ToolModule]] = {
    # Top-level compliance : entry-point classifier.
    "compliance": [
        diagnose_compliance_topic,
        ask_user_question,
    ],
    # Sub-agent registration (KYC, onboarding, premiers pas).
    "compliance.registration": [
        *_COMPLIANCE_BASE_TOOLS,
        propose_resume_registration,
        handoff_to_agent,
    ],
    # Sub-agent remediation (doc complémentaire, review, AML follow-up).
    # Phase 2c : peut handoff vers tx ou general APRÈS investigation.
    "compliance.remediation": [
        *_COMPLIANCE_BASE_TOOLS,
        handoff_to_agent,
        # Phase 2c : request_document_upload (L1) — différé Phase 3
    ],
    # Sub-agent transactional (état d'une opération).
    # Phase 2c : peut consult product pour composer une réponse riche
    # (délais, base produit). Pas de handoff (terminal côté chaîne).
    # Phase 2c.3 : `list_transactions` pour répondre aux demandes
    # de listes filtrées (« mes dépôts », « mes retraits »).
    # Phase 2c.5 : `stats_transaction_counts` + `stats_transaction_amounts`
    # pour répondre aux questions quantitatives (« combien »,
    # « montant total »). Lots 2 & 3 ajoutent
    # `stats_portfolio_performance` (markdown) et
    # `stats_portfolio_allocation` (embed donut).
    "compliance.transactional": [
        *_COMPLIANCE_BASE_TOOLS,
        read_transaction_detail,
        list_transactions,
        stats_transaction_counts,
        stats_transaction_amounts,
        stats_portfolio_performance,
        stats_portfolio_allocation,
        consult_specialist,
    ],
    # Fallback : exactement le scope Phase 2a (général, sans dispatcher).
    # Phase 2c : consult product + handoff vers spécialisations (rare).
    # Phase 2c.3 : `list_transactions` également exposé ici, en filet
    # de sécurité — si le diagnose route par erreur une question
    # transactionnelle vers `general` (regex incomplète, formulation
    # créative…), le LLM doit pouvoir produire un tableau Markdown
    # plutôt qu'improviser une liste à puces depuis `read_transactions`.
    # Phase 2c.5 : idem pour les stats, pour la même raison de filet.
    # Performance et allocation portfolio idem.
    "compliance.general": [
        *_COMPLIANCE_BASE_TOOLS,
        list_transactions,
        stats_transaction_counts,
        stats_transaction_amounts,
        stats_portfolio_performance,
        stats_portfolio_allocation,
        consult_specialist,
        handoff_to_agent,
    ],
    # Agent `product` Phase 2c (vrai agent runtime, plus stub).
    # Pas de `consult_specialist` ici : c'est un specialist terminal
    # (profondeur 1), il ne consulte personne.
    # Phase 2c.6 : ajout de `show_instrument_card` pour déclencher la
    # carte chat ``instrument_detail_card`` (complémentaire d'un texte
    # explicatif sur Bitcoin / Ether / etc.).
    # Phase 2 wiki : `select_wiki_pages` + `read_wiki_page` exposent les
    # 243 fiches markdown importées depuis le vault Obsidian source
    # (couverture large : FAQ, exclusive offers, crypto, account, etc.).
    # Temporairement désactivés (2026-05-06) — qualité éditoriale SQL
    # insuffisante ; toute lecture factuelle produit passe par le wiki MD
    # (`select_wiki_pages` + `read_wiki_page`). Réactiver en réimportant
    # `read_product_knowledge` / `list_product_knowledge_topics`.
    "product": [
        select_wiki_pages,
        read_wiki_page,
        # Phase FAQ CMS — liste d'articles HELP publiés (`article_type=HELP`)
        # avec slugs DB (complément du wiki MD). Pas de liens article
        # inventés dans le markdown : le widget porte les deep-links.
        show_featured_articles,
        show_instrument_card,
        # Phase 2 wiki — slider chat des bundles disponibles (catalogue
        # crypto_bundle public actif, source ``CatalogService``).
        show_crypto_bundles,
        # Phase 2 wiki v1.4 — fiche détaillée d'UN bundle (équivalent
        # ``show_instrument_card`` mais pour un bundle nommé). Utilisé
        # quand le client cible un bundle précis (« parle-moi du TOP5 »).
        show_bundle_detail,
        show_invest_source_accounts,
        show_invest_confirmation_draft,
        ask_user_question,
    ],
    # Phase 2c.6 : `advisor` peut aussi pousser la carte instrument
    # quand il évoque un actif dans un raisonnement d'allocation.
    # Phase 2c.7 : `advisor` peut citer des articles à la une +
    # commenter les mouvements crypto en complément de son conseil.
    # Router v2 (2026-05-04) : pattern **advisor-first** sur demandes
    # mixtes — l'advisor doit pouvoir interroger product et market via
    # `consult_specialist` pour synthétiser un conseil multi-angle
    # sans renvoyer le client sur 2 agents séparés.
    # Lot 1 « Wiki shared » (2026-05-06) — l'advisor doit pouvoir
    # citer la FAQ produit pour appuyer ses recommandations sans
    # déléguer systématiquement à `consult_specialist(product)`
    # (latence + tokens). Le filtre audience garantit qu'il ne voit
    # que les fiches `audience: client`.
    "advisor": [
        show_instrument_card,
        show_featured_articles,
        show_top_movers,
        select_wiki_pages,
        read_wiki_page,
        show_invest_source_accounts,
        show_invest_confirmation_draft,
        consult_specialist,
        ask_user_question,
    ],
    # Phase 2c.7 : agent `market` réveillé. Toolset L0 minimal centré
    # sur les widgets chat (articles à la une + top movers) — pas de
    # tool client/personnel ici (anti-tipping-off : market reste sur
    # les données publiques).
    # Lot 1 « Wiki shared » (2026-05-06) — accès lecture wiki client
    # pour cadrer les réponses (« comment fonctionne le swap ? »,
    # « qu'est-ce que la TVL ? ») via les fiches `concepts/`.
    "market": [
        show_featured_articles,
        show_top_movers,
        select_wiki_pages,
        read_wiki_page,
        ask_user_question,
    ],
    # Cognitive Bot v4 — Lot 4 (2026-05-04). Agent `trust` =
    # spécialiste Confiance & sécurité (régulation, custody, infra).
    # Toolset minimal : exploration du wiki ``faq/trust-security/`` via
    # `select_wiki_pages` + `read_wiki_page`. Pas de `consult_specialist`
    # (terminal, profondeur 1, ne consulte personne). Pas de tool
    # transactionnel ni produit : trust reste sur les preuves
    # factuelles, jamais le push commercial.
    "trust": [
        select_wiki_pages,
        read_wiki_page,
        ask_user_question,
    ],
    "action": [
        deposit_present_channels,
        crypto_investment_intent_start,
        crypto_investment_intent_resolve,
        crypto_investment_intent_confirm,
        crypto_buy_start,
        crypto_sell_start,
        crypto_swap_start,
        bundle_invest_start,
        ask_user_question,
    ],
    "default": [ask_user_question],
    # Le router ne passe **pas** par le runtime loop : il garde son
    # function-calling natif (cf. agents/router.py). Donc absent du registry.
}


# Tous les `agent_id` reconnus par le runtime (incl. sub-agents).
KNOWN_RUNTIME_AGENT_IDS: frozenset[str] = frozenset(TOOLS_BY_AGENT.keys())


# Topics compliance valides (pour la phase de dispatch).
COMPLIANCE_TOPICS: frozenset[str] = frozenset(
    {"registration", "remediation", "transactional", "general"}
)


def compliance_subagent_id(topic: str) -> str:
    """Mappe un `dominant_topic` → `agent_id` du sub-agent.

    Exemple : `"registration"` → `"compliance.registration"`.

    Si `topic` n'est pas dans `COMPLIANCE_TOPICS`, fallback sur
    `compliance.general` (jamais d'erreur).
    """
    safe_topic = (topic or "general").strip()
    if safe_topic not in COMPLIANCE_TOPICS:
        safe_topic = "general"
    return f"compliance.{safe_topic}"


def tools_for(agent_id: str) -> Sequence[ToolModule]:
    """Retourne la liste de modules-tools enregistrés pour un agent.

    Le filtrage par `autonomy_max` est volontairement **laissé au
    runtime** pour rester découplé : ici on retourne tout ce qui est
    *catalogué*, le runtime décide ce qui est *exposable au LLM*.

    Returns:
        Liste (potentiellement vide) de modules-tools. Jamais d'exception.
    """
    return list(TOOLS_BY_AGENT.get(agent_id) or [])


def find(agent_id: str, tool_name: str) -> ToolModule | None:
    """Résolution `tool_name → module` (linéaire, sufficient pour < 30 tools).

    Si `agent_id` n'est pas dans le registre, retourne `None` sans erreur
    (le runtime émet une erreur tool exploitable au LLM).
    """
    if not tool_name:
        return None
    for module in TOOLS_BY_AGENT.get(agent_id) or []:
        spec_name = (module.SPEC.get("function") or {}).get("name")  # type: ignore[union-attr]
        if spec_name == tool_name:
            return module
    return None


def all_tool_names(agent_id: str) -> list[str]:
    """Liste les noms canoniques des tools d'un agent (utile pour debug/tests)."""
    out: list[str] = []
    for module in TOOLS_BY_AGENT.get(agent_id) or []:
        spec_name = (module.SPEC.get("function") or {}).get("name")  # type: ignore[union-attr]
        if isinstance(spec_name, str) and spec_name:
            out.append(spec_name)
    return out
