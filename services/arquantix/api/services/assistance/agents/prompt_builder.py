"""Construction du payload OpenAI pour un agent à partir d'un AgentInput.

Stratégie d'assemblage commune (tous les agents passent par ici) :

  1. system #1 = system prompt **spécifique de l'agent** (chargé depuis
     `prompts/<agent_id>_system.md`).
  2. system #2 = bloc « mémoire long-terme cross-conv + résumé conv »,
     produit par `memory.build_context` (réutilise l'existant). N'est
     ajouté que si non-vide.
  3. user/assistant alternés = `recent_turns` du AgentInput.

Le user message courant est **déjà inclus** dans `recent_turns` (le
service.py persiste le user_msg avant d'appeler l'agent) ; lorsque
``compound_user_turn`` est présente dans ``memory_state``, la **dernière
ligne ``user`** de cet historique est réécrite avec la formulation
sémantique (assistant précédent + message court).

L'agent **n'a pas à** rajouter manuellement le dernier tour user séparément.

Si pour une raison quelconque le system prompt spécifique de l'agent
manque (fichier introuvable), un fallback minimal est utilisé pour
éviter de casser le tour. Un warning est loggé.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from services.assistance import memory as assistance_memory
from services.assistance.agents.base import AgentInput

from services.assistance.agents.conversation_continuity import (
    COMPOUND_USER_TURN_MEMORY_KEY,
    enrich_recent_turns_for_llm_semantic_user,
)
logger = logging.getLogger(__name__)

# NB: ``catalog_context_builder`` est importé en *lazy* dans
# ``_maybe_build_catalog_block`` pour briser un cycle d'import :
# ``runtime/__init__.py`` ré-exporte ``agent_loop`` qui importe
# ``prompt_builder.load_agent_system_prompt`` — un import top-level
# de ``runtime.catalog_context_builder`` ferait redéclencher
# ``runtime/__init__.py`` pendant l'init de ``prompt_builder`` lui-même.


_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_FALLBACK_PROMPT = (
    "Tu es un assistant Vancelian. Réponds en Markdown valide, en français, "
    "de manière claire, factuelle et concise. Pas de HTML brut."
)


# Cognitive Bot v4 — Lot 3 (2026-05-04). Whitelist des agents qui
# bénéficient du **Response Framework** auto-injecté en suffixe de leur
# system prompt. Le fragment partagé ``_response_framework.md`` impose
# une structure de réponse en 4 temps (ACK émotionnel → reformulation →
# apport de valeur → next best action) et s'aligne sur les blocs
# ``[OBJECTIVE]`` + ``[COGNITIVE STATE]`` injectés par
# ``agent_loop._build_initial_messages``.
#
# Sont **inclus** : agents qui produisent une réponse texte côté client.
# Sont **exclus** : `router` (function calling pur), `summarizer`
# (extraction JSON), `compliance` top-level (simple dispatcher).
RESPONSE_FRAMEWORK_AGENTS: frozenset[str] = frozenset({
    "default",
    "advisor",
    "product",
    "market",
    "compliance.registration",
    "compliance.transactional",
    "compliance.general",
    "compliance.remediation",
    # Lot 4 (anticipé) — agent Trust & Risk dédié à la rassurance.
    "trust",
})


_FRAMEWORK_FILE = _PROMPTS_DIR / "_response_framework.md"

# Wiki product — même `index.md` que le dépôt embarqué (`data/wiki/`).
# Injecté **uniquement** pour l'agent `product` afin de cartographier
# slugs et liens entre pages (équivalent « pass 1 » côté bot Slack).
_WIKI_INDEX_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "wiki" / "index.md"
)

# Cache module-level avec invalidation par mtime (reload en dev si le
# fichier change sans restart du process).
_wiki_index_cache_mtime: Optional[float] = None
_wiki_index_cache_block: Optional[str] = None


# Cache module-level — le fragment ne change pas pendant la durée de
# vie du process, on évite N relectures disque par tour.
_framework_cache: Optional[str] = None


def _load_response_framework_fragment() -> Optional[str]:
    """Charge le fragment Cognitive Bot v4 ``_response_framework.md``
    qui structure la réponse des agents experts en 4 temps.

    Best-effort : retourne ``None`` si le fichier n'existe pas (dégrade
    gracieusement vers le prompt agent seul, comme pré-Lot 3).
    Cache module-level pour éviter N relectures disque par tour.
    """
    global _framework_cache
    if _framework_cache is not None:
        return _framework_cache or None
    try:
        content = _FRAMEWORK_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.warning(
            "assistance.prompt_builder.response_framework_missing path=%s",
            _FRAMEWORK_FILE,
        )
        _framework_cache = ""  # marqueur : déjà tenté, échec
        return None
    except OSError as exc:
        logger.warning(
            "assistance.prompt_builder.response_framework_io_error exc=%s",
            exc,
        )
        _framework_cache = ""
        return None
    _framework_cache = content
    return content


def _load_product_wiki_index_block() -> str:
    """Lit ``index.md`` du wiki embarqué pour suffixer le prompt product.

    Best-effort : chaîne vide si le fichier est absent ou illisible
    (l'agent garde ``product_system.md`` + framework).
    """
    global _wiki_index_cache_mtime, _wiki_index_cache_block
    try:
        mtime = _WIKI_INDEX_FILE.stat().st_mtime
    except OSError:
        logger.warning(
            "assistance.prompt_builder.wiki_index_missing path=%s",
            _WIKI_INDEX_FILE,
        )
        return ""

    if (
        _wiki_index_cache_block is not None
        and _wiki_index_cache_mtime == mtime
    ):
        return _wiki_index_cache_block

    try:
        raw = _WIKI_INDEX_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning(
            "assistance.prompt_builder.wiki_index_read_error exc=%s",
            exc,
        )
        _wiki_index_cache_mtime = mtime
        _wiki_index_cache_block = ""
        return ""

    if not raw:
        _wiki_index_cache_mtime = mtime
        _wiki_index_cache_block = ""
        return ""

    block = (
        "## Wiki — index.md (cartographie des pages)\n\n"
        "Référence pour `read_wiki_page` : ce fichier liste les chemins des "
        "pages compilées et leur organisation. Sers-t'en pour choisir "
        "quels sujets lire et dans quel ordre, avant d'appeler l'outil.\n\n"
        "---\n\n"
        f"{raw}\n\n"
        "---"
    )
    _wiki_index_cache_mtime = mtime
    _wiki_index_cache_block = block
    return block


def _agent_id_to_path_stem(agent_id: str) -> str:
    """Normalise un `agent_id` pour chercher son prompt sur disque.

    Phase 2b — les sub-agents Compliance ont des IDs avec un point
    (`compliance.registration`). Pour le filesystem, on convertit en
    underscore (`compliance_registration`) afin que tous les noms de
    fichiers restent simples et POSIX-friendly.
    """
    return (agent_id or "").replace(".", "_")


def load_agent_system_prompt(agent_id: str) -> str:
    """Charge le system prompt spécifique de l'agent depuis le disque.

    Cherche `prompts/<agent_id_normalized>_system.md`. En cas d'absence ou
    de lecture impossible, retourne `_FALLBACK_PROMPT` et log un warning
    (best-effort).

    Le `agent_id` peut contenir un `.` pour les sub-agents (ex.
    `compliance.registration`) — il est normalisé en `_` pour le path.

    Cognitive Bot v4 — Lot 3 (2026-05-04) : pour les agents listés dans
    ``RESPONSE_FRAMEWORK_AGENTS``, on **concatène** automatiquement le
    fragment ``_response_framework.md`` qui impose la structure de
    réponse en 4 temps. Ainsi tous les agents experts héritent du
    framework sans duplication par fichier.

    Agent ``product`` : après le prompt fichier et avant le framework,
    on injecte ``data/wiki/index.md`` (cartographie des pages wiki) pour
    guider l'usage de ``read_wiki_page`` ; les autres agents ne reçoivent
    pas ce bloc.
    """
    stem = _agent_id_to_path_stem(agent_id)
    path = _PROMPTS_DIR / f"{stem}_system.md"
    base: str
    try:
        base = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.warning(
            "assistance.agent.prompt_missing agent=%s path=%s — using fallback",
            agent_id,
            path,
        )
        base = _FALLBACK_PROMPT
    except OSError as exc:
        logger.warning(
            "assistance.agent.prompt_io_error agent=%s exc=%s — using fallback",
            agent_id,
            exc,
        )
        base = _FALLBACK_PROMPT

    if agent_id == "product":
        wiki_block = _load_product_wiki_index_block()
        if wiki_block:
            base = base + "\n\n" + wiki_block

    if agent_id in RESPONSE_FRAMEWORK_AGENTS:
        framework = _load_response_framework_fragment()
        if framework:
            return base + "\n\n" + framework
    return base


def _maybe_build_catalog_block(agent_id: str) -> Optional[str]:
    """Construit le bloc-catalogue dynamique pour ``agent_id`` (best-effort).

    Le builder gère lui-même son cache TTL et ses erreurs DB. On ouvre ici une
    session SQLAlchemy ad-hoc et on la referme proprement. Toute exception est
    swallow et logguée — les agents continuent à tourner sans le bloc.

    NB: import lazy du builder pour briser le cycle ``prompt_builder ↔
    runtime.agent_loop`` qui transiterait par ``runtime/__init__.py``.
    """
    try:
        # Import lazy intentionnel — voir docstring du module.
        from services.assistance.agents.runtime.catalog_context_builder import (
            build_catalog_context_block,
            should_inject_catalog_for_agent,
        )
    except Exception:  # noqa: BLE001 — best-effort
        logger.warning(
            "assistance.prompt_builder.catalog_module_import_failed agent=%s",
            agent_id,
            exc_info=True,
        )
        return None

    if not should_inject_catalog_for_agent(agent_id):
        return None
    try:
        from database import SessionLocal  # import lazy
    except Exception:  # noqa: BLE001 — best-effort
        logger.warning(
            "assistance.prompt_builder.catalog_session_import_failed agent=%s",
            agent_id,
            exc_info=True,
        )
        return None

    db = None
    try:
        db = SessionLocal()
        return build_catalog_context_block(db)
    except Exception:  # noqa: BLE001 — best-effort
        logger.warning(
            "assistance.prompt_builder.catalog_block_failed agent=%s",
            agent_id,
            exc_info=True,
        )
        return None
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:  # noqa: BLE001 — best-effort
                pass


def build_agent_messages(
    *,
    agent_id: str,
    agent_input: AgentInput,
    extra_system_suffix: Optional[str] = None,
) -> list[dict]:
    """Construit le payload `messages` final pour un appel OpenAI.

    Args:
        agent_id: identifiant de l'agent (sert au chargement du prompt).
        agent_input: payload remis à l'agent par le service.
        extra_system_suffix: bloc Markdown additionnel concaténé au prompt
            système principal — utilisé par les agents qui veulent injecter
            le résultat de leurs tools (ex. compliance avec
            `get_account_status`) en *« contexte instantané »* avant la
            génération.

    Le prompt système final est composé de :

        1. Le system prompt chargé depuis disque (``load_agent_system_prompt``).
        2. *(Optionnel — si ``agent_id`` est dans la whitelist du builder)* le
           bloc « Catalogue Vancelian (vue dynamique) » généré depuis la table
           ``product_knowledge``. Best-effort : silencieux si DB indispo /
           kill-switch actif.
        3. *(Optionnel)* l'``extra_system_suffix`` fourni par l'agent
           (« Contexte instantané (tools) »).

    Returns:
        Liste de messages au format OpenAI : `[{role, content}, …]`.
    """
    system_prompt = load_agent_system_prompt(agent_id)

    catalog_block = _maybe_build_catalog_block(agent_id)
    catalog_section = catalog_block.strip() if catalog_block else ""

    extra_section = (
        extra_system_suffix.strip()
        if extra_system_suffix and extra_system_suffix.strip()
        else ""
    )

    sections: list[str] = [system_prompt]
    if catalog_section:
        sections.append(catalog_section)
    if extra_section:
        sections.append(f"## Contexte instantané (tools)\n{extra_section}")
    system_prompt = "\n\n".join(sections)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    memory_block = assistance_memory._format_memory_block(  # noqa: SLF001 — réuse interne assumé
        summary=(agent_input.memory_state or {}).get("conversation_summary"),
        client_long_memory=(agent_input.memory_state or {}).get("client_long_memory"),
    )
    if memory_block:
        messages.append({"role": "system", "content": memory_block})

    mem = agent_input.memory_state or {}
    cmpv = mem.get(COMPOUND_USER_TURN_MEMORY_KEY)
    compound_arg = (
        cmpv.strip()
        if isinstance(cmpv, str) and cmpv.strip()
        else None
    )
    turns_llm = enrich_recent_turns_for_llm_semantic_user(
        agent_input.recent_turns,
        compound_user_turn=compound_arg,
        raw_user_fallback=agent_input.user_message or "",
    )
    messages.extend(turns_llm or [])
    return messages
