"""Catalogue **documentation admin** pour l’agent ``action``.

Les **flux client** décrits ici sont un complément produit aux specs
OpenAI des tools (`SPEC["function"]["description"]`). Ils peuvent être
affinés sans toucher au runtime ; la liste des tools et la whitelist
CTA proviennent des modules canoniques pour limiter la dérive.

Persistance CMS / table : à brancher ultérieurement en remplacement
des champs ``client_flow_steps`` / ``title`` ci-dessous.
"""

from __future__ import annotations


from services.assistance.agents.tools.registry import tools_for
from services.assistance.agents.tools.shared.action_cta_catalog import (
    catalog_entries_for_admin,
)

DOC_REVISION = "2026-05-07"

_SOURCE_FILES_NOTE = (
    "services/assistance/agent_action_options_catalog.py (flux client — éditable)",
    "services/assistance/agents/tools/shared/action_cta_catalog.py (whitelist CTA)",
    "services/assistance/agents/tools/registry.py (tools par agent)",
)

# Clé = ``function.name`` du tool agent ``action``.
_ACTION_AGENT_FLOW_DOCS: dict[str, dict[str, Any]] = {
    "deposit_present_channels": {
        "title": "Choix du mode de dépôt",
        "client_flow_steps": [
            "Le client tape sur une option depuis la carte/widget assistance.",
            "L’app ouvre l’écran ou la modale de dépôt correspondant (virement SEPA, carte ou crypto entrant).",
            "Le client suit le flux natif (RIB/IBAN, autorisation carte, ou adresse réseau) jusqu’à confirmation.",
            "Aucun ordre ni prélèvement n’est exécuté depuis le chat : tout se passe côté app après navigation.",
        ],
        "related_cta_kinds": [
            "deposit_funds",
            "deposit_virement",
            "deposit_carte",
            "deposit_crypto",
        ],
    },
    "crypto_buy_start": {
        "title": "Achat crypto (entrée depuis l’assistant)",
        "client_flow_steps": [
            "Montant et symbole détectés (LLM et/ou analyse déterministe du message utilisateur).",
            "Si le montant est connu : **encart confirmation compact** (récap montant · source euro par défaut) puis navigation native au tap.",
            "Sinon : liste des comptes source autorisée ; lien avec montant facultatif lorsqu’indiqué.",
            "Confirmation et exécution dans les écrans applicatifs — rien depuis le backend chat hors navigation.",
        ],
        "related_cta_kinds": ["buy_instrument"],
    },
    "crypto_sell_start": {
        "title": "Vente crypto (deep-link résolu)",
        "client_flow_steps": [
            "Le serveur rattache le symbole à un instrument connu puis émet une CTA whitelistée « vendre ».",
            "Le client ouvre la fiche vendre correspondante dans l’app.",
            "Il saisit le montant puis confirme dans le flux de vente habituel.",
        ],
        "related_cta_kinds": ["sell_instrument", "view_instrument"],
    },
    "crypto_swap_start": {
        "title": "Échange / swap crypto",
        "client_flow_steps": [
            "L’assistant propose l’entrée liste marchés (et éventuellement des CTA contextuelles).",
            "Le client sélectionne les actifs et lance le flux « échanger » natif depuis l’écran marché.",
            "La suite (cotation, slippage, confirmation) suit le parcours app standard hors chat.",
        ],
        "related_cta_kinds": ["markets_crypto", "buy_instrument", "sell_instrument"],
    },
    "bundle_invest_start": {
        "title": "Investir dans un bundle",
        "client_flow_steps": [
            "L’assistant affiche les sources d’investissement autorisées pour ce bundle (réutilisation CAL).",
            "Le client choisit une source (ex. EUR ou wallet).",
            "L’app enchaîne sur le flux d’investissement bundle (montants, risques, confirmations) hors chat.",
        ],
        "related_cta_kinds": ["invest_bundle", "view_bundle_detail"],
    },
    "ask_user_question": {
        "title": "Clarification (transverse)",
        "client_flow_steps": [
            "Question ouverte dans le fil : le client répond dans le champ texte sans navigation app.",
            "Pas de deep-link ni d’effet financier jusqu’à ce qu’un autre tool émette une action.",
        ],
        "related_cta_kinds": [],
    },
}


def build_agent_action_options_payload() -> dict[str, Any]:
    """Construit la charge utile JSON pour l’admin (read-only)."""

    rows: list[dict[str, Any]] = []
    for module in tools_for("action"):
        spec = getattr(module, "SPEC", None) or {}
        fn = (spec.get("function") or {}) if isinstance(spec, dict) else {}
        tool_name = fn.get("name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            continue
        llm_desc = ""
        raw_desc = fn.get("description")
        if isinstance(raw_desc, str):
            llm_desc = raw_desc.strip()
        autonomy = ""
        au = spec.get("autonomy_level") if isinstance(spec, dict) else None
        if isinstance(au, str):
            autonomy = au.strip()

        doc_block = _ACTION_AGENT_FLOW_DOCS.get(tool_name, {})
        title = doc_block.get("title")
        if not isinstance(title, str) or not title.strip():
            title = tool_name
        raw_steps = doc_block.get("client_flow_steps") or []
        steps: list[str] = []
        if isinstance(raw_steps, list):
            for s in raw_steps:
                if isinstance(s, str) and s.strip():
                    steps.append(s.strip())

        rc = doc_block.get("related_cta_kinds") or []
        kinds: list[str] = []
        if isinstance(rc, list):
            for k in rc:
                if isinstance(k, str) and k.strip():
                    kinds.append(k.strip())

        rows.append(
            {
                "tool_name": tool_name,
                "title": title.strip(),
                "tool_description_llm": llm_desc,
                "autonomy_level": autonomy or "unknown",
                "client_flow_steps": steps,
                "related_cta_kinds": kinds,
            }
        )

    return {
        "doc_revision": DOC_REVISION,
        "source_files_note": list(_SOURCE_FILES_NOTE),
        "action_agent_tools": rows,
        "cta_whitelist": catalog_entries_for_admin(),
    }


__all__ = ["DOC_REVISION", "build_agent_action_options_payload"]
