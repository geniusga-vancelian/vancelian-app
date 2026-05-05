"""Agent ``trust`` — Trust & Risk (Cognitive Bot v4 — Lot 4).

Spécialiste de la **rassurance** : régulation, custody, infrastructure,
sécurité, gestion des risques opérationnels (hacks, faillites,
custody-cold-storage). Différenciateur clé de Vancelian dans l'univers
RWA / crypto.

──────────────────────────────────────────────────────────────────────
Pattern hybride (cf. choix user 2026-05-04, option mixte A+B+C)
──────────────────────────────────────────────────────────────────────

  * **(A) Agent racine routable** — le router peut désigner directement
    `trust` quand la demande est purement sécurité/régulation/custody/
    hack (cf. règle 5.7 du `router_system.md`). Pas le cas le plus
    fréquent mais utile sur les questions ciblées.

  * **(B) Specialist consultable** — `advisor` (et `compliance.general`)
    peuvent appeler `consult_specialist(target="trust", purpose=
    "reassure_about_regulation"|"reassure_about_custody"|
    "reassure_about_security")` pour obtenir un encart factuel à
    intégrer dans leur réponse synthétique. C'est le cas le plus
    fréquent : un client en FEAR posté sur un advisor a besoin de
    fond rassurant que seul `trust` sait livrer correctement.

  * **(C) Couche transverse** — pas un agent en soi, mais le wiki
    ``faq/trust-security/`` est lisible par tous via `read_wiki_page`
    → tout agent peut puiser dans la même source de vérité.

──────────────────────────────────────────────────────────────────────
Toolset minimal V1
──────────────────────────────────────────────────────────────────────

  * ``select_wiki_pages`` + ``read_wiki_page`` — exploite les fiches
    ``faq/trust-security/*.md`` (régulation, custody, infrastructure).
  * ``ask_user_question`` — transverse, pour qualifier une crainte
    précise quand le message est vague.

Pas de tool transactionnel ni produit : `trust` est sur les **preuves
factuelles**, jamais le push.

Référence d'archi : `docs/arquantix/COGNITIVE_BOT.md` § B4.
"""

from __future__ import annotations

from services.assistance.agents._llm_agent_base import LLMAgentBase
from services.assistance.agents.base import AGENT_LABELS, AGENT_TRUST_ID


class TrustAgent(LLMAgentBase):
    """Agent narratif spécialisé Confiance & Sécurité."""

    agent_id: str = AGENT_TRUST_ID
    display_label: str = AGENT_LABELS[AGENT_TRUST_ID]
    model_env_var: str = "ASSISTANCE_AGENT_TRUST_MODEL"
    # Température légèrement basse — les réponses sécurité/régulation
    # doivent rester factuelles et calmes (pas de créativité narrative).
    _default_temperature: float = 0.3
