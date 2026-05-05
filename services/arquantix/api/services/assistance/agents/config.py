"""Configuration centralisée des env vars du système multi-agents.

Toutes les fonctions ici lisent les env vars **à chaque appel** (pas de
caching module-level) pour permettre au monkeypatch des tests de prendre
effet, et à un opérateur de changer un modèle en prod via redéploiement
sans rebuild d'image.

Référence : `docs/arquantix/MULTI_AGENTS.md` § 5.
"""

from __future__ import annotations

import os

from services.assistance.config import OPENAI_MODEL


def assistance_multi_agent_enabled() -> bool:
    """Kill-switch global. False → 100% legacy `default` agent (cf. § 5.2)."""
    raw = (os.getenv("ASSISTANCE_MULTI_AGENT_ENABLED") or "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def assistance_router_model() -> str:
    """Modèle utilisé par le router pour classifier l'intention."""
    return os.getenv("ASSISTANCE_AGENT_ROUTER_MODEL") or OPENAI_MODEL


def assistance_router_temperature() -> float:
    """Température du router. Défaut très bas pour stabilité de la classification."""
    try:
        v = float(os.getenv("ASSISTANCE_ROUTER_TEMPERATURE", "0.1"))
    except ValueError:
        v = 0.1
    return max(0.0, min(2.0, v))


def assistance_router_confidence_min() -> float:
    """Seuil sous lequel le router doit déclencher un QCM (cf. § 1.9).

    Clampé dans [0.0, 1.0]. Hors de cet intervalle → 0.5.
    """
    try:
        v = float(os.getenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.5"))
    except ValueError:
        v = 0.5
    if not (0.0 <= v <= 1.0):
        v = 0.5
    return v


def assistance_router_hot_path_enabled() -> bool:
    """Active le **hot-path follow-up** du router (Phase 2 wiki v1.4 patch).

    Quand activé : un message user court (≤ `assistance_router_hot_path_max_chars`)
    qui suit immédiatement un tour d'agent expert (i.e. dernier message
    assistant émis par `product`/`compliance`/`advisor`/`market`)
    **bypasse** l'appel LLM router et conserve l'agent précédent.

    Défaut : `true` — économie ~150-300 ms et stabilité conversationnelle
    (cf. analyse `5bef01e9` 2026-05-04 où le router avait flippé entre
    `product` et `market` sur 3 follow-ups consécutifs sur le même bundle).

    Override : `ASSISTANCE_ROUTER_HOT_PATH_ENABLED=false` pour désactiver
    en cas de régression observée en production.
    """
    raw = os.getenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def assistance_router_hot_path_max_chars() -> int:
    """Longueur max d'un user message éligible au hot-path (Phase 2 wiki
    v1.4 patch).

    Défaut : 60 caractères. Au-delà, on ne fait pas l'hypothèse que
    le message est un follow-up court (questions ouvertes plus longues
    méritent une vraie classification LLM).

    Clampé dans [10, 300].
    """
    try:
        v = int(os.getenv("ASSISTANCE_ROUTER_HOT_PATH_MAX_CHARS", "60"))
    except ValueError:
        v = 60
    return max(10, min(300, v))


def assistance_wiki_llm_retriever_enabled() -> bool:
    """Active le **Karpathy LLM-as-retriever** sur le wiki (Phase 2 wiki
    v1.4 patch 3).

    Quand activé : `select_wiki_pages` appelle d'abord un LLM avec un
    catalogue compact des 222+ fiches FAQ ; le LLM choisit 3-5 slugs
    pertinents. Fallback transparent sur le scoring keyword si l'appel
    échoue. Cf. `services/assistance/agents/repositories/wiki_llm_retriever.py`.

    Défaut : `true` — corrige les rates de matching FR↔EN observés en
    prod (cf. analyse conv `534d545b` 2026-05-04 où `select_wiki_pages`
    retourne 0 match sur « parle moi des offres exclusives » alors que
    34 fiches existent).

    Override : `ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED=false` pour
    revenir au comportement d'origine en cas de régression.
    """
    raw = os.getenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def assistance_wiki_llm_retriever_model() -> str:
    """Modèle utilisé par le retriever LLM. Défaut : modèle agent
    `product` (cohérence + reuse caches OpenAI). Override :
    `ASSISTANCE_WIKI_LLM_RETRIEVER_MODEL`."""
    return (
        os.getenv("ASSISTANCE_WIKI_LLM_RETRIEVER_MODEL")
        or assistance_agent_model("product")
    )


def assistance_wiki_llm_retriever_max_slugs() -> int:
    """Nombre max de slugs retournés par le retriever LLM (cap).

    Défaut : 5. Clampé dans [1, 10] — au-delà, le LLM caller a trop de
    candidats et risque de boucler.
    """
    try:
        v = int(os.getenv("ASSISTANCE_WIKI_LLM_RETRIEVER_MAX_SLUGS", "5"))
    except ValueError:
        v = 5
    return max(1, min(10, v))


def assistance_agent_model(agent_id: str) -> str:
    """Modèle OpenAI à utiliser pour l'agent ``agent_id``.

    Résolution :
      1. `ASSISTANCE_AGENT_<ID>_MODEL` (ex. `ASSISTANCE_AGENT_ADVISOR_MODEL`).
      2. `ASSISTANCE_OPENAI_MODEL` (override commun assistance).
      3. `OPENAI_MODEL` (défaut global API).
      4. `"gpt-4o-mini"` (fallback dur).
    """
    var_name = f"ASSISTANCE_AGENT_{agent_id.upper()}_MODEL"
    return (
        os.getenv(var_name)
        or os.getenv("ASSISTANCE_OPENAI_MODEL")
        or OPENAI_MODEL
        or "gpt-4o-mini"
    )


def assistance_agent_temperature(agent_id: str, *, default: float = 0.7) -> float:
    """Température override-able par agent.

    `ASSISTANCE_AGENT_<ID>_TEMPERATURE` ou défaut produit. Clampé [0, 2].
    """
    var_name = f"ASSISTANCE_AGENT_{agent_id.upper()}_TEMPERATURE"
    raw = os.getenv(var_name)
    if raw is None:
        return max(0.0, min(2.0, default))
    try:
        v = float(raw)
    except ValueError:
        return max(0.0, min(2.0, default))
    return max(0.0, min(2.0, v))


# ─────────────────────────────────────────────────────────────────────────
# Phase 2a — Runtime agent loop config
# Cf. docs/arquantix/MULTI_AGENTS_RUNTIME.md § 1.2 & § 3
# ─────────────────────────────────────────────────────────────────────────


def _parse_int_env(var_name: str, *, default: int, lo: int, hi: int) -> int:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        v = int(raw)
    except ValueError:
        return default
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def assistance_agent_max_iter() -> int:
    """Nombre max d'itérations du runtime loop (cf. RUNTIME § 1.2).

    Borne hard `[1, 20]`. Au-delà de la borne, on clampe (sécurité contre
    les valeurs aberrantes en prod). Défaut **6**.
    """
    return _parse_int_env(
        "ASSISTANCE_AGENT_MAX_ITER", default=6, lo=1, hi=20
    )


def assistance_agent_timeout_seconds() -> int:
    """Timeout total d'un tour agent (somme des itérations).

    Borne hard `[5, 120]`. Défaut **25** s. Si dépassé, le runtime émet
    `error: agent_timeout` et persiste le partiel.
    """
    return _parse_int_env(
        "ASSISTANCE_AGENT_TIMEOUT_SECONDS", default=25, lo=5, hi=120
    )


def assistance_tool_timeout_seconds() -> int:
    """Timeout par appel de tool (DB query, repo, provider externe).

    Borne hard `[1, 30]`. Défaut **5** s. Si dépassé, le tool retourne
    `{"error": "timeout"}` au LLM (qui peut s'auto-corriger ou abandonner).
    """
    return _parse_int_env(
        "ASSISTANCE_TOOL_TIMEOUT_SECONDS", default=5, lo=1, hi=30
    )


_AUTONOMY_LEVELS = ("L0", "L1", "L2", "L3")


def _normalize_autonomy(raw: str | None, *, default: str = "L0") -> str:
    """Normalise une valeur d'autonomie env. Fallback `L0` (mode safe)."""
    if raw is None:
        return default
    v = raw.strip().upper()
    if v in _AUTONOMY_LEVELS:
        return v
    return default


def assistance_global_autonomy_killswitch() -> bool:
    """Kill-switch global d'autonomie (cf. RUNTIME § 3.4).

    Quand `True` (défaut), tous les agents sont contraints à `L0`
    (read-only) quel que soit leur paramètre individuel — utilisé en cas
    d'incident.

    Défaut **True** : Phase 2a livre uniquement L0 partout, donc le
    kill-switch est *fail-safe* : par défaut on coupe les mutations.
    Quand on activera Phase 2c, on devra explicitement passer
    `ASSISTANCE_GLOBAL_AUTONOMY_KILLSWITCH=false` pour autoriser L1+.
    """
    raw = (
        os.getenv("ASSISTANCE_GLOBAL_AUTONOMY_KILLSWITCH") or "true"
    ).strip().lower()
    return raw in ("1", "true", "yes", "on")


def assistance_product_slack_pipeline_enabled() -> bool:
    """Pipeline multi-phases type bot Slack (guardrail entrée → Pass 1 sur
    ``index.md`` → chargement fiches → agent → juge sortie optionnel).

    Désactivable avec ``ASSISTANCE_PRODUCT_SLACK_PIPELINE_ENABLED=false``.

    Défaut **true** : pipeline aligné bot Slack (guardrail → Pass 1 index →
    pré-chargement wiki → agent). Désactive en cas de régression.
    """
    raw = (
        os.getenv("ASSISTANCE_PRODUCT_SLACK_PIPELINE_ENABLED") or "true"
    ).strip().lower()
    return raw in ("1", "true", "yes", "on")


def assistance_product_pipeline_index_max_chars() -> int:
    """Troncature defensive de ``index.md`` pour le Pass 1 (0 = illimité).

    Clampé à [0, 500_000]. Défaut 0 (= pas de troncature).
    """
    try:
        v = int(os.getenv("ASSISTANCE_PRODUCT_PIPELINE_INDEX_MAX_CHARS", "0"))
    except ValueError:
        v = 0
    return max(0, min(500_000, v))


def assistance_product_pipeline_page_max_chars() -> int:
    """Taille max du corps par fiche injectée (Pass 3). Défaut 3000."""
    return _parse_int_env(
        "ASSISTANCE_PRODUCT_PIPELINE_PAGE_MAX_CHARS",
        default=3000,
        lo=500,
        hi=50_000,
    )


def assistance_product_pipeline_output_judge_enabled() -> bool:
    """Juge de sortie (PASS / REWRITE / BLOCK). Bufferise la réponse
    jusqu'au ``done`` si activé.

    Quand activé, les scores (5 critères 1–5), ``confidence``,
    ``knowledge_gap`` et flags sont normalisés et persistés dans
    ``message_payload.metadata.product_pipeline_output_judge`` ainsi
    que dans l'event SSE ``done.product_pipeline_output_judge``.

    Défaut **true**. Désactive avec
    ``ASSISTANCE_PRODUCT_PIPELINE_OUTPUT_JUDGE_ENABLED=false`` si latence
    ou coût trop élevés.
    """
    raw = (
        os.getenv("ASSISTANCE_PRODUCT_PIPELINE_OUTPUT_JUDGE_ENABLED") or "true"
    ).strip().lower()
    return raw in ("1", "true", "yes", "on")


def assistance_product_pipeline_model() -> str:
    """Modèle pour guardrail entrée, Pass 1 index et juge sortie.

    Défaut : même modèle que l'agent ``product``.
    """
    return os.getenv("ASSISTANCE_PRODUCT_PIPELINE_MODEL") or assistance_agent_model(
        "product"
    )


def assistance_product_guardrail_enabled() -> bool:
    """Phase 2 wiki — guard-rail anti-hallucination de l'agent ``product``.

    Quand activé (**défaut True**), le runtime intercepte les réponses
    finales de l'agent ``product`` qui n'auraient appelé **aucun** tool
    de lecture (``read_product_knowledge``, ``read_wiki_page``,
    ``show_instrument_card``) **ou** qui auraient appelé
    ``select_wiki_pages`` **sans** suivre par ``read_wiki_page`` /
    ``read_product_knowledge``. Dans ce cas, un message system rappelant
    le contrat est injecté et la boucle réitère **une seule fois**. Si le
    second essai produit toujours une réponse non-sourcée, on laisse
    passer (mieux qu'un fallback vide).

    Pour désactiver en cas d'incident :
    ``ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED=false``.
    """
    raw = (
        os.getenv("ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED") or "true"
    ).strip().lower()
    return raw in ("1", "true", "yes", "on")


def assistance_agent_autonomy_max(agent_id: str) -> str:
    """Niveau d'autonomie max autorisé pour un agent.

    Lit `ASSISTANCE_<AGENT>_AUTONOMY_MAX` (ex. `ASSISTANCE_COMPLIANCE_AUTONOMY_MAX=L0`).
    Si `assistance_global_autonomy_killswitch()` est `True`, force `L0`.
    Défaut individuel : `L0` (mode safe Phase 2a).

    Returns:
        Une chaîne dans `{"L0", "L1", "L2", "L3"}`.
    """
    if assistance_global_autonomy_killswitch():
        return "L0"
    var_name = f"ASSISTANCE_{agent_id.upper()}_AUTONOMY_MAX"
    return _normalize_autonomy(os.getenv(var_name), default="L0")


def autonomy_le(level: str, max_level: str) -> bool:
    """`level <= max_level` selon l'ordre L0 < L1 < L2 < L3."""
    if level not in _AUTONOMY_LEVELS:
        return False
    if max_level not in _AUTONOMY_LEVELS:
        return False
    return _AUTONOMY_LEVELS.index(level) <= _AUTONOMY_LEVELS.index(max_level)


def assistance_stream_thinking_enabled() -> bool:
    """Active l'événement SSE `thinking` (debug/admin only). Défaut False.

    Cf. RUNTIME § 8.1 : ne **JAMAIS** activer en prod côté mobile —
    cela exposerait les tools appelés et les arguments LLM, source
    potentielle de tipping-off.
    """
    raw = (
        os.getenv("ASSISTANCE_STREAM_THINKING") or "false"
    ).strip().lower()
    return raw in ("1", "true", "yes", "on")


def assistance_runtime_loop_enabled() -> bool:
    """Active le runtime agent loop (Phase 2a). Défaut **False**.

    Quand `True`, les agents qui possèdent des tools dans
    `tools/registry.py` sont dispatchés via `runtime.run_agent_loop` au
    lieu du `agent.stream(...)` Phase 1. Les autres agents conservent
    leur flux Phase 1 sans changement (pas de régression).

    Mise en prod : passer à `True` après validation smoke test pour
    activer le mode multi-tools sur l'agent compliance. Rollback
    instantané en cas de souci → repasser à `False` (zéro rebuild).
    """
    raw = (
        os.getenv("ASSISTANCE_RUNTIME_LOOP_ENABLED") or "false"
    ).strip().lower()
    return raw in ("1", "true", "yes", "on")


def assistance_runtime_loop_agents() -> set[str]:
    """Liste des agents pour lesquels le runtime loop est actif.

    `ASSISTANCE_RUNTIME_LOOP_AGENTS=compliance,product,advisor,market`
    (défaut `compliance,product,advisor,market`). Permet d'opt-in agent
    par agent, indépendamment du kill-switch global.

    Phase 2c : `product` est ajouté au défaut pour permettre :
      - le dispatch direct via router (questions produit/délais),
      - les `consult_specialist` cross-agent depuis compliance.

    Phase 2c.7 : `advisor` et `market` sont également activés par
    défaut pour exposer les nouveaux widgets chat (cartes instrument,
    articles à la une, top movers crypto) — sans cela, leur stream
    reste en mode Phase 1 streaming Markdown sans tool calls.
    """
    raw = os.getenv("ASSISTANCE_RUNTIME_LOOP_AGENTS")
    if raw is None or not raw.strip():
        return {"compliance", "product", "advisor", "market"}
    return {part.strip().lower() for part in raw.split(",") if part.strip()}
