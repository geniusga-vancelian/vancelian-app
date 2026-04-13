"""
State machine for Finance Strategy Chat (phases 0-7).
"""
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from .store import STORE
from .schemas import StartRequest, StepRequest, StartResponse, StepResponse, StateResponse, Message, UIState
from .ai import analyze_project, analyze_project_and_prefill, compose_phase7_recap, compose_step_message, compose_final_advisor_recap, compose_indicative_calculation, compose_micro_feedback, compose_clarity_helper, interpret_user_answer
from .schemas import AnswerInterpretation
from .catalog import list_offers
from .next_question import choose_next_question, load_default_registry


DEFAULT_TTL_SECONDS = 60 * 60  # 1 hour
TOTAL_PHASES = 7
MIN_AI_TEXT_LEN = 40
CONFIDENCE_THRESHOLD = 0.72
MAX_CLARIFICATIONS = 2
EXCLUSIVE_TARGET_PCT = 10
CONF_USER_TEXT = 0.9
CONF_USER_CHOICE = 0.95
CONF_INFERRED = 0.7
CONF_DEFAULT = 0.5

QUESTIONS_REGISTRY = load_default_registry()


PHASE_PROMPTS = {
    0: (
        "👋 Tu vas voir, c’est très simple et ça prend moins d’une minute.\n\n"
        "Je suis là pour te guider dans la création d’un plan d’épargne sur mesure,\n"
        "adapté à ton projet personnel et à tes envies — sans jargon financier compliqué.\n\n"
        "👉 Raconte-moi ton projet, comme il te vient.\n"
        "Je suis là pour t’aider à y voir clair et t’orienter pour la suite."
    ),
    1: (
        "Raconte-moi librement ton **projet d’épargne** :  \n"
        "un **objectif**, une **envie**, un **projet de vie**…  \n"
        "Même si ce n’est pas encore très clair, **tu ne peux pas te tromper**."
    ),
    2: (
        "Pour certains projets, se fixer un **cap chiffré** aide beaucoup.\n"
        "Pour d’autres, l’important est surtout d’épargner régulièrement — les deux sont très bien.\n\n"
        "Dans ton cas, tu dirais plutôt :"
    ),
    3: (
        "Pendant cette période, est-ce que tu penses avoir besoin d’utiliser une partie de cet argent avant ton projet ?\n"
        "Si oui, à quelle fréquence aimerais-tu pouvoir y accéder ?"
    ),
    4: (
        "Imaginons que ton portefeuille baisse temporairement sur une période donnée.\n"
        "Laquelle de ces réactions te ressemble le plus ?"
    ),
    5: (
        "Pour ce projet, souhaites-tu rester sur une approche très sécurisée,\n"
        "ou es-tu ouvert à structurer une partie de la stratégie afin d’en améliorer\n"
        "le potentiel de rendement sur la durée ?"
    ),
    6: "Phase 6/7 — Souhaites-tu du stock picking sur des offres exclusives ?",
}

PHASE_2_AMOUNT_EXACT_PROMPT = "Tu as un montant en tête, même approximatif ?"
PHASE_2_AMOUNT_RANGE_PROMPT = "Tu penses plutôt à quelle fourchette ?"
PHASE_2_RECURRING_PROMPT = "Tu préfères mettre de côté régulièrement, ou quand tu peux ?"
PHASE_2_INITIAL_CONTRIBUTION_PROMPT = (
    "Tu penses pouvoir mettre une somme au départ, ou on part uniquement sur du mensuel ?"
)
PHASE_2_MONTHLY_CONTRIBUTION_PROMPT = "Et côté mensuel, tu te situes où ?"
PHASE_3_SAVINGS_RHYTHM_PROMPT = (
    "Pour atteindre cet objectif, est-ce que tu imagines plutôt mettre de l’argent régulièrement "
    "(par exemple chaque mois), ou plutôt faire des versements ponctuels quand tu le peux ?"
)
PHASE_5_TARGET_AMOUNT_PROMPT = (
    "🎯 **Pour aller un peu plus loin**,  \n"
    "as-tu en tête un **objectif précis** pour ce projet ?\n\n"
    "Par exemple :\n"
    "- un montant à atteindre,\n"
    "- ou simplement l’idée de mettre de côté “le plus possible”.\n\n"
    "Les deux sont très bien — dis-moi ce qui te parle le plus."
)

PHASE_2_TEMPLATE = {
    "prudent": (
        "Pour certains projets, se fixer un **cap chiffré** aide beaucoup.\n"
        "Pour d’autres, l’important est surtout d’épargner régulièrement — les deux sont très bien.\n\n"
        "Dans ton cas, tu dirais plutôt :"
    ),
    "equilibre": (
        "Pour certains projets, se fixer un **cap chiffré** aide beaucoup.\n"
        "Pour d’autres, l’important est surtout d’épargner régulièrement — les deux sont très bien.\n\n"
        "Dans ton cas, tu dirais plutôt :"
    ),
    "ambitieux": (
        "Pour certains projets, se fixer un **cap chiffré** aide beaucoup.\n"
        "Pour d’autres, l’important est surtout d’épargner régulièrement — les deux sont très bien.\n\n"
        "Dans ton cas, tu dirais plutôt :"
    ),
}

PHASE_3_TEMPLATE = {
    "prudent": (
        "Sur une période longue, il est important de se sentir en sécurité face aux imprévus.\n"
        "La disponibilité de ton épargne contribue directement à ta tranquillité d’esprit.\n"
        "Quelle liberté souhaites-tu conserver sur ton épargne ?"
    ),
    "equilibre": (
        "Même avec une vision long terme, certains besoins peuvent apparaître en cours de route.\n"
        "La liquidité permet d’adapter la stratégie sans la remettre en cause.\n"
        "Quelle liberté souhaites-tu conserver sur ton épargne ?"
    ),
    "ambitieux": (
        "Ton horizon permet d’envisager une stratégie structurée dans le temps.\n"
        "Il reste néanmoins utile d’anticiper d’éventuels besoins de trésorerie.\n"
        "Quelle liberté souhaites-tu conserver sur ton épargne ?"
    ),
}

PHASE_4_TEMPLATE = {
    "prudent": (
        "Certaines variations peuvent être inconfortables, surtout lorsqu’on pense à l’avenir.\n"
        "L’important est de rester dans une zone où tu es à l’aise dans le temps.\n"
        "Quelle description te correspond le mieux ?"
    ),
    "equilibre": (
        "Un bon équilibre consiste à accepter une part de mouvement sans perdre en sérénité.\n"
        "La clé est d’adopter un niveau de risque que tu pourras assumer durablement.\n"
        "Quelle description te correspond le mieux ?"
    ),
    "ambitieux": (
        "Pour viser davantage de potentiel, il faut parfois accepter des phases de variation.\n"
        "L’essentiel est que cela reste cohérent avec ton projet global.\n"
        "Quelle description te correspond le mieux ?"
    ),
}

PHASE_5_TEMPLATE = {
    "prudent": (
        "À ce stade, l’objectif est de construire une stratégie qui te ressemble.\n"
        "Certaines préférences ou contraintes peuvent renforcer ton confort.\n"
        "Souhaites-tu préciser des éléments particuliers ?"
    ),
    "equilibre": (
        "La structure de la stratégie se dessine progressivement.\n"
        "Des préférences personnelles peuvent aider à l’affiner.\n"
        "Souhaites-tu préciser certains points ?"
    ),
    "ambitieux": (
        "La stratégie peut être optimisée selon tes convictions ou tes priorités.\n"
        "C’est le moment d’exprimer ce qui compte vraiment pour toi.\n"
        "Souhaites-tu ajouter des éléments spécifiques ?"
    ),
}

PHASE_5_SHORT_TERM_PROMPT = (
    "Pour un objectif à court terme, on privilégie la simplicité et la stabilité.\n"
    "Quelle approche te semble la plus confortable ?"
)


def _build_offers_text() -> str:
    offers = list_offers()
    lines = ["Projets disponibles :"]
    for o in offers:
        lines.append(
            f"- {o['project_id']} — {o['title']} ({o['location']}), "
            f"{o['duration_months']} mois, cible {o['target_apr_range']}, "
            f"min {o['min_ticket']} — {o['summary']}"
        )
    return "\n".join(lines)


def _filtered_offers_for_horizon(state: Dict[str, Any]) -> list:
    offers = list_offers()
    answers = state.get("answers", {})
    horizon_value = (answers.get("horizon") or {}).get("value") or state.get("horizon") or ""
    horizon_value = str(horizon_value).lower()
    if "mid_term" in horizon_value:
        return [o for o in offers if int(o.get("duration_months", 0)) <= 36]
    return offers


def _build_offers_text_for_state(state: Dict[str, Any]) -> str:
    offers = _filtered_offers_for_horizon(state)
    if not offers:
        return "Aucun projet compatible actuellement."
    lines = ["Projets disponibles :"]
    for o in offers:
        lines.append(
            f"- {o['project_id']} — {o['title']} ({o['location']}), "
            f"{o['duration_months']} mois, cible {o['target_apr_range']}, "
            f"min {o['min_ticket']} — {o['summary']}"
        )
    return "\n".join(lines)


def _allocation_ui_for_state(state: Dict[str, Any]) -> UIState:
    offers = _filtered_offers_for_horizon(state)
    cards = [
        {"id": o["project_id"], "title": o["title"], "description": o["summary"]}
        for o in offers
    ]
    return UIState(
        type="allocation_picker",
        allocation_picker={
            "min": 0,
            "max": 100,
            "step": 5,
            "max_total": EXCLUSIVE_TARGET_PCT,
            "cards": cards,
        },
        allow_free_text=False,
    )


def _build_recap(state: Dict[str, Any]) -> str:
    project_text = state.get("project_text", "")
    summary = state.get("summary", "")
    horizon = state.get("horizon", "")
    liquidity = state.get("liquidity", "")
    risk_profile = state.get("risk_profile", "")
    risk_behavior = state.get("risk_behavior", "")
    exclusive = state.get("exclusive_offers_choice", "")
    strategy = state.get("strategy_construction", "")

    risk_map = {
        "prudent": "plutôt prudent",
        "balanced": "équilibré",
        "dynamic": "à l’aise avec les variations",
        "bucketed": "nuancé, avec une partie plus dynamique",
    }
    strategy_map = {
        "secure": "très sécurisée",
        "balanced": "équilibrée",
        "optimized": "orientée optimisation sur la durée",
    }

    intention = summary or project_text or "ton projet"
    risk_phrase = risk_map.get(risk_profile, risk_behavior or "nuancé")
    strategy_phrase = strategy_map.get(strategy, strategy or "équilibrée")
    exclusive_phrase = "tu es ouvert aux offres exclusives" if "accept" in exclusive.lower() else "tu souhaites rester sur des options classiques"

    return (
        "Voici la synthèse de ton projet telle que nous l’avons comprise.\n"
        f"Tu souhaites {intention}. "
        f"Tu te projettes sur un horizon {horizon} avec une liquidité {liquidity}. "
        f"Ton rapport au risque est plutôt {risk_phrase}, "
        f"et tu privilégies une approche {strategy_phrase}. "
        f"Enfin, {exclusive_phrase}.\n"
        "Cette stratégie restera évolutive et ajustable dans le temps."
    )


def _format_phase7_recap(recap: Dict[str, Any]) -> str:
    title = recap.get("title", "").strip()
    markdown = recap.get("markdown", "").strip()
    disclaimer = recap.get("disclaimer", "").strip()
    lines = []
    if title:
        lines.append(title)
    if markdown:
        lines.append("")
        lines.append(markdown)
    if disclaimer:
        lines.append("")
        lines.append(f"_{disclaimer}_")
    return "\n".join(lines)


def _phase7_next_message(tone_style: str) -> str:
    if tone_style == "prudent":
        return "Et ensuite ? Tu peux activer cette stratégie en douceur, ou revenir sur un point pour ajuster."
    if tone_style == "ambitieux":
        return "Et ensuite ? Tu peux mettre en place cette stratégie maintenant, ou revenir sur un point pour itérer."
    return "Et ensuite ? Tu peux activer cette stratégie, ou revenir sur un point pour ajuster."


def _phase7_activation_message(tone_style: str) -> str:
    if tone_style == "prudent":
        return "Parfait, la stratégie est prête. Nous pourrons démarrer progressivement et ajuster au besoin."
    if tone_style == "ambitieux":
        return "Parfait, la stratégie est prête. Nous pourrons la mettre en place et itérer selon tes priorités."
    return "Parfait, la stratégie est prête. Nous pourrons l’activer et ajuster ensuite si nécessaire."


def _maybe_append_indicative_calc(session: Dict[str, Any], messages: list) -> None:
    # Indicative calculation is shown only when objective and duration are reliable
    answers = session.get("answers", {})
    target = answers.get("target_amount") or {}
    if not target or float(target.get("confidence") or 0) < 0.8:
        return
    horizon_months = (answers.get("horizon_months") or {}).get("value")
    if not horizon_months:
        horizon_value = (answers.get("horizon") or {}).get("value") or session.get("horizon")
        horizon_months = _parse_horizon_to_months(horizon_value)
        if horizon_months:
            answers["horizon_months"] = _answer_value(horizon_months, CONF_INFERRED, "inferred")
    if not horizon_months:
        return
    initial = answers.get("initial_contribution_amount") or {}
    monthly = answers.get("monthly_contribution_amount") or {}
    has_contribution = False
    if initial.get("value") is not None and float(initial.get("confidence") or 0) >= 0.85:
        has_contribution = True
    if monthly.get("value") is not None and float(monthly.get("confidence") or 0) >= 0.85:
        has_contribution = True
    if not has_contribution:
        return

    if session.get("indicative_calculation"):
        return
    try:
        result = compose_indicative_calculation(session.get("answers", {}))
        if result.message:
            session["indicative_calculation"] = result.message
            messages.append(Message(role="assistant", content=result.message))
    except Exception:
        return


def _answer_value(value: Any, confidence: float, source: str) -> Dict[str, Any]:
    return {
        "value": value,
        "confidence": confidence,
        "source": source,
        "updated_at": datetime.utcnow().isoformat(),
    }


def _init_answers_state() -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    def _blank():
        return {"value": None, "confidence": CONF_DEFAULT, "source": "default", "updated_at": now}
    return {
        "project_summary": _blank(),
        "project_type": _blank(),
        "project_clarity": _blank(),
        "intent": _blank(),
        "horizon": _blank(),
        "liquidity": _blank(),
        "liquidity_internal": _blank(),
        "risk": _blank(),
        "risk_question_policy": _blank(),
        "target_amount": _blank(),
        "target_amount_type": _blank(),
        "initial_contribution_amount": _blank(),
        "monthly_contribution_amount": _blank(),
        "contribution_currency": _blank(),
        "contribution_notes": _blank(),
        "recurring_saving": _blank(),
        "recurring_amount": _blank(),
        "savings_rhythm": _blank(),
        "funding_plan_status": _answer_value("incomplete", CONF_DEFAULT, "default"),
        "strategy_preference": _blank(),
        "exclusives_opt_in": _blank(),
        "exclusives_allocations": {"value": {}, "confidence": CONF_DEFAULT, "source": "default", "updated_at": now},
        "tone_style": _blank(),
    }


def should_ask(field_name: str, answers: Dict[str, Any], threshold: float = 0.85) -> bool:
    if not answers or field_name not in answers:
        return True
    field = answers.get(field_name) or {}
    value = field.get("value")
    confidence = field.get("confidence") or 0
    if value is None or value == "":
        return True
    return float(confidence) < threshold


def _skip_question(session_id: str, session: Dict[str, Any], messages: list, key: str, last_user_text: str = "") -> StepResponse:
    session["debug_skip_question_key"] = key
    session["debug_skip_reason"] = "already_known"
    return _ask_next(session_id, session, messages, last_user_text)


def _project_hint_message() -> str:
    return (
        "Pas de souci 🙂  \n"
        "C’est très courant de ne pas avoir un projet précis au départ.\n"
        "Pour t’aider, voici quelques exemples de projets d’épargne possibles.\n"
        "Dis-moi simplement ce qui se rapproche le plus de ton envie."
    )


def _project_hint_options() -> list:
    return [
        "🏖️ Préparer un projet plaisir (vacances, voyage, achat important)",
        "🏡 Mettre de l’argent de côté pour un futur achat",
        "🌱 Épargner pour l’avenir sans objectif précis",
        "🧓 Préparer ma retraite ou le long terme",
        "💬 Je ne sais pas encore, j’aimerais qu’on en parle",
    ]


def _is_vague_project_input(text: str) -> bool:
    if not text:
        return True
    stripped = text.strip().lower()
    if len(stripped.split()) < 6:
        return True
    triggers = [
        "je sais pas",
        "j sais pas",
        "aide",
        "aide moi",
        "aide-moi",
        "aucune idée",
        "peu importe",
        "je ne sais pas",
    ]
    return any(token in stripped for token in triggers)


def _prompt_project_guidance(session_id: str, session: Dict[str, Any], messages: list, last_user_message: Optional[str] = None) -> StepResponse:
    helper = {}
    try:
        helper = compose_clarity_helper(last_user_message or "", session.get("summary"))
    except Exception:
        helper = {}
    message = helper.get("message") or _project_hint_message()
    messages.append(Message(role="assistant", content=message))
    return _ask_next(session_id, session, messages, last_user_message or "")


def _help_user_clarify_project(session_id: str, session: Dict[str, Any], input_text: str) -> StepResponse:
    raw = (input_text or "").strip()
    lower = raw.lower()
    intent_hint = session.get("summary") or session.get("project_text") or raw
    if "chanel" in lower or "luxe" in lower or "plaisir" in lower:
        intro = "Je vois très bien 🙂 On va faire ça proprement ensemble."
    else:
        intro = "Merci pour ce que tu as partagé 🙂 On va clarifier tout ça, pas à pas."
    messages = [
        Message(role="assistant", content=intro),
    ]
    session["intent_hint"] = intent_hint
    return _ask_next(session_id, session, messages, input_text)


def _maybe_append_micro_feedback(session: Dict[str, Any], messages: list, last_user_message: str) -> None:
    if not last_user_message:
        return
    answers = session.get("answers", {})
    context = {
        "project_summary": (answers.get("project_summary") or {}).get("value") or session.get("summary"),
        "horizon_human": _display_horizon((answers.get("horizon") or {}).get("value")),
        "target_amount_or_null": (answers.get("target_amount") or {}).get("value"),
        "initial_amount_or_null": (answers.get("initial_contribution_amount") or {}).get("value"),
        "monthly_amount_or_null": (answers.get("monthly_contribution_amount") or {}).get("value"),
        "liquidity_label_or_null": (answers.get("liquidity") or {}).get("value"),
        "last_user_message": last_user_message,
    }
    try:
        feedback = compose_micro_feedback(context)
        if feedback and feedback.message:
            messages.append(Message(role="assistant", content=feedback.message))
    except Exception:
        return


def _apply_answer_updates(session: Dict[str, Any], updates: list) -> None:
    if not updates or "answers" not in session:
        return
    for upd in updates:
        try:
            key = upd.key if hasattr(upd, "key") else upd.get("key")
            value = upd.value if hasattr(upd, "value") else upd.get("value")
            confidence = upd.confidence if hasattr(upd, "confidence") else upd.get("confidence")
            source = upd.source if hasattr(upd, "source") else upd.get("source") or "user_text"
        except Exception:
            continue
        if not key:
            continue
        session["answers"][key] = _answer_value(value, float(confidence or 0.5), str(source))


def _try_interpret_answer(
    session_id: str,
    session: Dict[str, Any],
    messages: list,
    step_id: str,
    question_text: str,
    expected_key: str,
    user_text: str,
) -> Optional[AnswerInterpretation]:
    try:
        interpretation = interpret_user_answer(
            state=session,
            step_id=step_id,
            question_text=question_text,
            expected_key=expected_key,
            user_text=user_text,
        )
    except Exception:
        return None
    updates = interpretation.updates or []
    _apply_answer_updates(session, updates)
    if interpretation.derived and "answers" in session:
        for key, value in interpretation.derived.items():
            session["answers"][key] = _answer_value(value, CONF_INFERRED, "inferred")
    if "no_progress_count" not in session:
        session["no_progress_count"] = 0
    if not updates:
        session["no_progress_count"] += 1
    else:
        has_strong = any(
            float(getattr(u, "confidence", 0) if hasattr(u, "confidence") else u.get("confidence", 0)) >= 0.7
            for u in updates
        )
        session["no_progress_count"] = 0 if has_strong else session["no_progress_count"] + 1
    if interpretation.assistant_ack:
        messages.append(Message(role="assistant", content=interpretation.assistant_ack))
    if interpretation.routed_to:
        session["debug_routed_to"] = interpretation.routed_to
    if interpretation.routing_reason:
        session["debug_routing_reason"] = interpretation.routing_reason
    if interpretation.next:
        session["debug_interpretation_next"] = interpretation.next.question
    return interpretation


def next_best_question(session: Dict[str, Any], last_user_text: str) -> Dict[str, Any]:
    project_clarity = _ans_val(session, "project_clarity")
    project_summary_conf = _ans_conf(session, "project_summary")
    if (project_clarity != "clear" or project_summary_conf < 0.7) and (
        "je sais pas" in (last_user_text or "").lower() or _is_vague_project_input(last_user_text or "")
    ):
        return {
            "step_id": "clarify_intent",
            "question_text": "Tu veux plutôt viser quoi avec cette épargne ?",
            "ui": {
                "type": "quick_replies",
                "allow_free_text": True,
                "quick_replies": [
                    "Voyage ou plaisir",
                    "Achat important",
                    "Mettre de côté sans objectif précis",
                    "Préparer le long terme",
                ],
            },
            "reason": "project_vague",
        }

    if _is_missing(session, "target_amount", 0.8):
        return {
            "step_id": "collect_budget",
            "question_text": "Tu as une idée du budget, même approximative ? Sinon on l’estime ensemble.",
            "ui": {"type": "free_text", "allow_free_text": True, "quick_replies": ["On estime ensemble", "Je ne sais pas"]},
            "reason": "budget_missing",
        }

    if _is_missing(session, "horizon", 0.75):
        return {
            "step_id": "collect_horizon",
            "question_text": "Dans combien de temps idéalement ?",
            "ui": {"type": "free_text", "allow_free_text": True, "quick_replies": ["< 1 an", "1–3 ans", "> 3 ans"]},
            "reason": "horizon_missing",
        }

    if _is_missing(session, "initial_contribution_amount", 0.8):
        return {
            "step_id": "funding_initial",
            "question_text": PHASE_2_INITIAL_CONTRIBUTION_PROMPT,
            "ui": {"type": "free_text", "allow_free_text": True, "quick_replies": ["500€", "2 000€", "Je ne sais pas"]},
            "reason": "initial_missing",
        }

    if _is_missing(session, "monthly_contribution_amount", 0.8):
        return {
            "step_id": "funding_monthly",
            "question_text": PHASE_2_MONTHLY_CONTRIBUTION_PROMPT,
            "ui": {"type": "free_text", "allow_free_text": True, "quick_replies": ["100€/mois", "250€/mois", "Je ne sais pas"]},
            "reason": "monthly_missing",
        }

    if session.get("vault_offer_done"):
        return {
            "step_id": "recap",
            "question_text": "Parfait. Tu veux ajuster quelque chose avant qu’on avance ?",
            "ui": {"type": "free_text", "allow_free_text": True},
            "reason": "vault_done",
        }
    return {
        "step_id": "offer_vault",
        "question_text": "On crée un coffre d’épargne dédié et on avance ensemble. Tu veux qu’on le lance ?",
        "ui": {"type": "quick_replies", "allow_free_text": True, "quick_replies": ["Oui", "Plus tard"]},
        "reason": "ready_for_vault",
    }


def _topic_prompt_and_options(topic: str, session: Dict[str, Any]) -> tuple[str, list[str]]:
    if topic == "target_amount":
        return PHASE_2_AMOUNT_EXACT_PROMPT, ["10 000€", "25 000€", "Je préfère avancer sans chiffre"]
    if topic == "initial_contribution_amount":
        return PHASE_2_INITIAL_CONTRIBUTION_PROMPT, ["500€", "2 000€", "Je ne sais pas encore"]
    if topic == "monthly_contribution_amount":
        return PHASE_2_MONTHLY_CONTRIBUTION_PROMPT, ["100€/mois", "250€/mois", "Je préfère en parler après"]
    if topic == "liquidity":
        return _phase3_prompt(session), ["Accès à tout moment", "Occasionnellement", "Uniquement à l’échéance", "Pas besoin d’y toucher"]
    if topic == "strategy_preference":
        return PHASE_5_STRATEGY_PROMPT, ["Approche très sécurisée", "Approche équilibrée", "Approche optimisée sur la durée"]
    return "Parfait. On passe à la suite.", []


def _build_question_state(session: Dict[str, Any]) -> Dict[str, Any]:
    answers = session.get("answers") or {}
    mapped = {}

    def _map(src: str, dest: str) -> None:
        entry = answers.get(src) or {}
        value = entry.get("value")
        if value is None or value == "":
            return
        mapped[dest] = {
            "value": value,
            "confidence": float(entry.get("confidence") or 0.0),
        }

    _map("project_type", "goal.type")
    _map("intent", "goal.type")
    _map("project_summary", "goal.description")
    _map("target_amount", "goal.target_amount")
    _map("initial_contribution_amount", "goal.initial_contribution_amount")
    _map("monthly_contribution_amount", "capacity.monthly_contribution")
    _map("horizon", "timeline.horizon_months")
    _map("liquidity", "capacity.liquidity_need")
    _map("project_clarity", "project_clarity")

    summary = session.get("summary") or session.get("project_text")
    if summary and "goal.description" not in mapped:
        mapped["goal.description"] = {"value": summary, "confidence": CONF_INFERRED}

    return {"answers": mapped}


def _ask_next(session_id: str, session: Dict[str, Any], messages: list, last_user_text: str = "") -> StepResponse:
    state = _build_question_state(session)
    choice = choose_next_question(state, QUESTIONS_REGISTRY)
    step_id = choice["step_id"]
    question_text = choice["question_text"]
    ui = choice["ui"]
    reason = choice["reason"]

    goal_type_entry = (state.get("answers") or {}).get("goal.type") or {}
    session["debug_last_selector"] = "choose_next_question"
    session["debug_next_step_id"] = step_id
    session["debug_next_reason"] = reason
    session["debug_project_type"] = {
        "value": goal_type_entry.get("value"),
        "confidence": goal_type_entry.get("confidence"),
    }

    if session.get("no_progress_count", 0) >= 2 and ui.get("quick_replies"):
        ui["type"] = "quick_replies"
        ui["allow_free_text"] = True

    message = _render_assistant_message(step_id, session, question_text, ui.get("quick_replies") or [])
    messages.append(Message(role="assistant", content=message))

    session["step_id"] = step_id
    session["updated_at"] = datetime.utcnow().isoformat()
    STORE.update(session_id, session, DEFAULT_TTL_SECONDS)
    return StepResponse(
        session_id=session_id,
        messages=messages,
        ui=UIState(type=ui["type"], quick_replies=ui.get("quick_replies"), allow_free_text=ui.get("allow_free_text", True)),
        progress=_progress(session.get("phase", 2)),
        state=session,
    )

def _apply_project_hint_choice(choice: str, session: Dict[str, Any]) -> None:
    mapping = {
        "🏖️ Préparer un projet plaisir (vacances, voyage, achat important)": (
            "projet_plaisir",
            "préparer un projet plaisir (vacances, voyage ou achat important)",
        ),
        "🏡 Mettre de l’argent de côté pour un futur achat": (
            "futur_achat",
            "mettre de l’argent de côté pour un futur achat",
        ),
        "🌱 Épargner pour l’avenir sans objectif précis": (
            "avenir_sans_objectif",
            "épargner pour l’avenir sans objectif précis",
        ),
        "🧓 Préparer ma retraite ou le long terme": (
            "retraite_long_terme",
            "préparer la retraite ou un projet long terme",
        ),
        "💬 Je ne sais pas encore, j’aimerais qu’on en parle": (
            "aide_guidée",
            "clarifier ton projet d’épargne avec un accompagnement guidé",
        ),
    }
    if choice not in mapping:
        return
    intent_value, summary_value = mapping[choice]
    session["intent"] = intent_value
    session["summary"] = summary_value
    session["confidence"] = 0.9
    session["project_text"] = summary_value
    session["question"] = None
    if "answers" in session:
        session["answers"]["intent"] = _answer_value(intent_value, CONF_USER_CHOICE, "user_choice")
        session["answers"]["project_summary"] = _answer_value(summary_value, CONF_USER_CHOICE, "user_choice")
    _update_project_synthesis(session, summary_value)


def _ans_val(session: Dict[str, Any], key: str) -> Any:
    return (session.get("answers", {}).get(key) or {}).get("value")


def _ans_conf(session: Dict[str, Any], key: str) -> float:
    return float((session.get("answers", {}).get(key) or {}).get("confidence") or 0.0)


def _is_known(session: Dict[str, Any], key: str, threshold: float = 0.85) -> bool:
    value = _ans_val(session, key)
    return value not in (None, "", []) and _ans_conf(session, key) >= threshold


def _is_missing(session: Dict[str, Any], key: str, threshold: float = 0.85) -> bool:
    return not _is_known(session, key, threshold)


def _infer_project_type(text: str) -> tuple[str, float]:
    lower = text.lower()
    mapping = [
        ("voyage", ["voyage", "vacances", "trip", "week-end"]),
        ("achat_plaisir", ["plaisir", "cadeau", "achat", "shopping"]),
        ("retour_aux_etudes", ["études", "formation", "école"]),
        ("retraite", ["retraite", "long terme"]),
        ("achat_immobilier", ["immobilier", "appartement", "maison"]),
    ]
    for project_type, keywords in mapping:
        if any(k in lower for k in keywords):
            return project_type, 0.8
    if lower.strip() in ("je sais pas", "je ne sais pas", "pas sûr", "aucune idée"):
        return "flou", 0.9
    return "autre", 0.5


def _update_project_synthesis(session: Dict[str, Any], last_user_text: str) -> None:
    if "answers" not in session:
        return
    summary = _ans_val(session, "project_summary") or last_user_text
    if summary:
        proj_type, proj_conf = _infer_project_type(str(summary))
        session["answers"]["project_type"] = _answer_value(proj_type, proj_conf, "inferred")
        clarity = "vague" if _is_vague_project_input(str(summary)) else "clear"
        clarity_conf = 0.8 if clarity == "clear" else 0.7
        session["answers"]["project_clarity"] = _answer_value(clarity, clarity_conf, "inferred")


def _continue_after_project_summary(session_id: str, session: Dict[str, Any], messages: list) -> StepResponse:
    mission = _maybe_send_mission_statement(session_id, session, messages)
    if mission:
        return mission
    funding = _maybe_enter_funding_plan(session_id, session, messages)
    if funding:
        return funding
    return _ask_next(session_id, session, messages, session.get("last_user_message") or "")


def _has_confident_goal(session: Dict[str, Any]) -> bool:
    answers = session.get("answers", {})
    intent = answers.get("intent") or {}
    if intent.get("value") and float(intent.get("confidence") or 0) >= 0.7:
        return True
    summary = answers.get("project_summary") or {}
    if summary.get("value") and float(summary.get("confidence") or 0) >= 0.7:
        return True
    target = answers.get("target_amount") or {}
    if target.get("value") is not None and float(target.get("confidence") or 0) >= 0.7:
        return True
    monthly = answers.get("monthly_contribution_amount") or {}
    if monthly.get("value") is not None and float(monthly.get("confidence") or 0) >= 0.7:
        return True
    return False


def _mission_statement_message(session: Dict[str, Any]) -> str:
    summary = (session.get("summary") or (session.get("answers", {}).get("project_summary") or {}).get("value") or "ce projet").strip()
    summary_line = summary.rstrip(".")
    return f"Pour {summary_line}, on crée un coffre d’épargne dédié et on avance ensemble."


def _maybe_send_mission_statement(session_id: str, session: Dict[str, Any], messages: list) -> Optional[StepResponse]:
    if session.get("mission_statement_sent"):
        return None
    if not _has_confident_goal(session):
        return None
    messages.append(Message(role="assistant", content=_mission_statement_message(session)))
    session["mission_statement_sent"] = True
    return _ask_next(session_id, session, messages, session.get("last_user_message") or "")


def _transition_message(field_name: str, value: Any) -> str:
    if field_name == "horizon":
        return f"Parfait — je note que tu te situes sur un horizon {_display_horizon(value)}. Passons à la suite."
    if field_name == "liquidity":
        return _liquidity_ack(_normalize_liquidity_label(value))
    if field_name == "risk":
        return "Parfait — je note ton niveau de confort face aux variations. Passons à la suite."
    if field_name == "strategy_preference":
        return "Parfait — je note ta préférence de construction. Passons à la suite."
    return "Parfait — passons à la suite."


def _display_horizon(value: Any) -> str:
    horizon = str(value or "").lower()
    mapping = {
        "short_term": "court terme (moins d’un an)",
        "mid_term": "1 à 3 ans",
        "long_term": "3 à 5 ans",
        "very_long": "au-delà de 5 ans",
    }
    for key, label in mapping.items():
        if key in horizon:
            return label
    return str(value) if value else "—"


def _display_liquidity(value: Any) -> str:
    raw = str(value or "").lower()
    if "accès à tout moment" in raw or "quotidienne" in raw or raw == "high":
        return "élevée (accès à tout moment)"
    if "mensuelle" in raw or raw == "medium":
        return "moyenne (accès occasionnel)"
    if "uniquement à l’échéance" in raw or "uniquement a l'échéance" in raw:
        return "faible (uniquement à l’échéance)"
    if "faible liquidité" in raw or raw in {"low", "very_low"} or "faible" in raw:
        return "faible"
    if "occasionnellement" in raw:
        return "moyenne (accès occasionnel)"
    if "pas besoin" in raw:
        return "faible"
    return str(value) if value else "—"


def _normalize_liquidity_label(value: Any) -> str:
    raw = str(value or "").lower()
    if "pas besoin" in raw or raw == "very_low":
        return "Pas besoin d’y toucher"
    if "accès à tout moment" in raw or "quotidienne" in raw or raw == "high":
        return "Accès à tout moment"
    if "occasionnellement" in raw or "mensuelle" in raw or raw == "medium":
        return "Occasionnellement"
    if "uniquement à l’échéance" in raw or "uniquement a l'échéance" in raw or raw == "low":
        return "Uniquement à l’échéance"
    if "faible" in raw:
        return "Uniquement à l’échéance"
    return str(value) if value else "—"


def _liquidity_internal(label: str) -> str:
    raw = str(label or "").lower()
    if "accès à tout moment" in raw:
        return "high"
    if "occasionnellement" in raw:
        return "medium"
    if "uniquement à l’échéance" in raw or "uniquement a l'échéance" in raw:
        return "low"
    if "pas besoin" in raw:
        return "very_low"
    return "medium"


def _liquidity_ack(label: str) -> str:
    if "pas besoin" in str(label).lower():
        return "OK, je note que tu n’as pas besoin d’y toucher pendant la période."
    if label == "Occasionnellement":
        return "OK, je note que tu veux garder une certaine flexibilité, sans besoin d’accès permanent."
    if label == "Accès à tout moment":
        return "OK, je note que tu veux garder un accès à tout moment."
    if label == "Uniquement à l’échéance":
        return "OK, je note que tu n’as pas besoin d’accès avant l’échéance."
    return "OK, je note ta préférence de liquidité."


def _risk_policy(state: Dict[str, Any]) -> tuple[str, str]:
    answers = state.get("answers", {})
    policy = (answers.get("risk_question_policy") or {}).get("value")
    if policy in {"skip", "soft_confirm", "explicit"}:
        return policy, "answers"
    policy = state.get("risk_question_policy")
    if policy in {"skip", "soft_confirm", "explicit"}:
        return policy, "top_level"
    if _is_short_term_horizon(state):
        return "skip", "inferred"
    return "explicit", "inferred"


def _phase5_options(state: Dict[str, Any]) -> list:
    if _is_short_term_horizon(state):
        return [
            "Approche très sécurisée",
            "Approche prudente avec un peu d’optimisation (sans volatilité)",
        ]
    return [
        "Approche très sécurisée",
        "Approche équilibrée",
        "Approche optimisée sur la durée",
    ]


def _phase5_prompt(state: Dict[str, Any]) -> str:
    if _is_short_term_horizon(state):
        return PHASE_5_SHORT_TERM_PROMPT
    return PHASE_PROMPTS[5]


def _advance_to_phase5_after_risk_skip(session_id: str, session: Dict[str, Any], messages: list) -> StepResponse:
    if _should_ask_savings_rhythm(session):
        return _ask_next(session_id, session, messages)
    answers = session.get("answers", {})
    risk_value = (answers.get("risk") or {}).get("value") or {}
    if isinstance(risk_value, dict):
        session["risk_profile"] = risk_value.get("profile") or "capital_protection"
        session["risk_score"] = risk_value.get("score")
        session["risk_behavior"] = risk_value.get("choice")
    if "answers" in session and not (answers.get("risk") or {}).get("value"):
        session["answers"]["risk"] = _answer_value(
            {"profile": "capital_protection"},
            CONF_INFERRED,
            "inferred",
        )
    messages.append(Message(
        role="assistant",
        content="Pour un projet aussi proche, l’essentiel est de protéger ton capital et de garder de la flexibilité. Passons à la suite."
    ))
    return _ask_next(session_id, session, messages)


def _risk_options(policy: str) -> list:
    if policy == "soft_confirm":
        return [
            "Je préfère limiter fortement les variations",
            "J’accepte de petites variations si c’est maîtrisé",
            "Je suis ouvert à une petite part plus dynamique",
        ]
    return [
        "Je privilégie la stabilité",
        "Je préfère un équilibre",
        "Je suis à l’aise avec des variations",
        "Ça dépend : seulement une partie plus dynamique",
    ]


def _map_risk_choice(choice: str, policy: str) -> Dict[str, Any]:
    if policy == "soft_confirm":
        if "limiter fortement" in choice:
            return {"profile": "capital_protection", "score": 20}
        if "petites variations" in choice:
            return {"profile": "cautious_growth", "score": 45}
        return {"profile": "balanced", "score": 60}
    # explicit
    if "stabilité" in choice:
        return {"profile": "capital_protection", "score": 20}
    if "équilibre" in choice:
        return {"profile": "balanced", "score": 50}
    if "variations" in choice and "partie" not in choice:
        return {"profile": "growth_oriented", "score": 75}
    return {"profile": "bucketed", "score": 60}


def detect_tone_style(state: Dict[str, Any]) -> str:
    text = f"{state.get('project_text', '')} {state.get('summary', '')}".lower()
    safe_words = [
        "sécurité",
        "sécuriser",
        "préserver",
        "protéger",
        "sans risque",
        "prudent",
        "stable",
        "sérénité",
        "tranquillité",
        "enfants",
        "retraite",
        "réserve",
        "imprévu",
        "dormir",
        "stress",
    ]
    growth_words = [
        "performance",
        "croissance",
        "opportunité",
        "dynamiser",
        "optimiser",
        "rendement",
        "ambitieux",
        "maximiser",
        "accélérer",
        "investir plus",
        "long terme",
        "construire",
    ]
    safe_score = sum(1 for w in safe_words if w in text)
    growth_score = sum(1 for w in growth_words if w in text)

    risk_score = state.get("risk_score")
    if isinstance(risk_score, int) and risk_score <= 35:
        safe_score += 2
    if isinstance(risk_score, int) and risk_score >= 70:
        growth_score += 2

    liquidity = (state.get("liquidity") or "").lower()
    if "quotidienne" in liquidity:
        safe_score += 1
    if "faible" in liquidity:
        growth_score += 1

    if safe_score - growth_score >= 2:
        return "prudent"
    if growth_score - safe_score >= 2:
        return "ambitieux"
    return "equilibre"


def _render_assistant_message(step_id: str, state: Dict[str, Any], question_text: str, options_list: list) -> str:
    tone_style = detect_tone_style(state)
    state["tone_style"] = tone_style
    if "answers" in state:
        state["answers"]["tone_style"] = _answer_value(tone_style, CONF_INFERRED, "inferred")
    phase_guidance = {
        "phase_2_amount_type": "Clarifier un cap chiffré si nécessaire, sans pression.",
        "phase_3": "Explorer le besoin de liquidité sans répéter le projet.",
        "phase_4": "Aborder le confort face aux variations uniquement si pertinent.",
        "phase_5": "Faire choisir une posture de stratégie, sans jargon produit.",
    }.get(step_id)
    try:
        rendered = compose_step_message(
            state=state,
            step_id=step_id,
            tone_style=tone_style,
            question_text=question_text,
            options_list=options_list,
            phase_guidance=phase_guidance,
        ).message
        return rendered or question_text
    except Exception:
        templates = {
            "phase_2_amount_type": PHASE_2_TEMPLATE,
            "phase_2_recurring": {"prudent": PHASE_2_RECURRING_PROMPT, "equilibre": PHASE_2_RECURRING_PROMPT, "ambitieux": PHASE_2_RECURRING_PROMPT},
            "phase_3": PHASE_3_TEMPLATE,
            "phase_4": PHASE_4_TEMPLATE,
            "phase_5": PHASE_5_TEMPLATE,
        }
        return templates.get(step_id, PHASE_3_TEMPLATE).get(tone_style, question_text)


def _infer_long_term_horizon(project_text: str, summary: str) -> bool:
    text = f"{project_text} {summary}".lower()
    signals = [
        "long terme",
        ">5",
        "5 ans",
        "10 ans",
        "15 ans",
        "18 ans",
        "déblocage",
        "enfants",
        "retraite",
        "études",
        "université",
    ]
    return any(s in text for s in signals)


def _is_short_term_horizon(state: Dict[str, Any]) -> bool:
    answers = state.get("answers", {})
    horizon_value = (answers.get("horizon") or {}).get("value") or state.get("horizon") or ""
    horizon_value = str(horizon_value).lower()
    return "short_term" in horizon_value or "court terme" in horizon_value or "<2 ans" in horizon_value


def _phase3_prompt(state: Dict[str, Any]) -> str:
    base = (
        "Pendant cette période, est-ce que tu penses avoir besoin d’utiliser une partie de cet argent avant ton projet ?\n"
        "Si oui, à quelle fréquence aimerais-tu pouvoir y accéder ?"
    )
    if _is_short_term_horizon(state):
        tone_guidance = (state.get("tone_guidance") or "").lower()
        if "rassurant" in tone_guidance or "sérénité" in tone_guidance:
            return base + "\nL’objectif est de préserver ton confort et ta flexibilité."
        return base + "\nCela nous aide à rester sereins face aux imprévus."
    return base


def _has_recurring_hint(state: Dict[str, Any]) -> bool:
    text = f"{state.get('project_text', '')} {state.get('summary', '')}".lower()
    signals = [
        "petit a petit",
        "petit à petit",
        "chaque mois",
        "mensuel",
        "mensuelle",
        "mensuellement",
        "tous les mois",
        "chaque semaine",
        "hebdo",
        "régulier",
        "régulièrement",
        "mettre de côté",
    ]
    return any(s in text for s in signals)


def _should_ask_recurring(state: Dict[str, Any]) -> bool:
    answers = state.get("answers", {})
    if not should_ask("recurring_saving", answers, 0.85):
        return False
    monthly = answers.get("monthly_contribution_amount") or {}
    if monthly.get("value") and float(monthly.get("confidence") or 0) >= 0.85:
        return False
    if _is_short_term_horizon(state):
        return _has_recurring_hint(state)
    return True


def _should_ask_savings_rhythm(state: Dict[str, Any]) -> bool:
    answers = state.get("answers", {})
    savings = answers.get("savings_rhythm") or {}
    if savings.get("value") is not None and float(savings.get("confidence") or 0) >= 0.75:
        return False
    monthly = answers.get("monthly_contribution_amount") or {}
    if monthly.get("value") is not None and float(monthly.get("confidence") or 0) >= 0.85:
        return False
    recurring = answers.get("recurring_saving") or {}
    if recurring.get("value") is not None and float(recurring.get("confidence") or 0) >= 0.85:
        return False
    target = answers.get("target_amount") or {}
    if target.get("value") is None or float(target.get("confidence") or 0) < 0.8:
        return False
    if not should_ask("savings_rhythm", answers, 0.85):
        return False
    return True


def _infer_savings_rhythm_from_amount(session: Dict[str, Any]) -> None:
    answers = session.get("answers")
    if not answers:
        return
    monthly = answers.get("monthly_contribution_amount") or {}
    if monthly.get("value") is None or float(monthly.get("confidence") or 0) < 0.85:
        return
    current = answers.get("savings_rhythm") or {}
    if current.get("value") is not None and float(current.get("confidence") or 0) >= 0.85:
        return
    answers["savings_rhythm"] = _answer_value("regular", 0.95, "inferred")


def _should_ask_target_amount(state: Dict[str, Any]) -> bool:
    answers = state.get("answers", {})
    target = answers.get("target_amount") or {}
    target_type = answers.get("target_amount_type") or {}
    if target.get("value") is not None and float(target.get("confidence") or 0) >= 0.85:
        return False
    if target_type.get("value") and float(target_type.get("confidence") or 0) >= 0.85:
        return False
    return True


def _has_confirmed_target(state: Dict[str, Any]) -> bool:
    answers = state.get("answers", {})
    target = answers.get("target_amount") or {}
    if target.get("value") is not None and float(target.get("confidence") or 0) >= 0.85:
        return True
    target_type = answers.get("target_amount_type") or {}
    if target_type.get("value") in {"exact", "range"} and float(target_type.get("confidence") or 0) >= 0.85:
        return True
    return False


def _should_ask_initial_contribution(state: Dict[str, Any]) -> bool:
    answers = state.get("answers", {})
    if not _has_confirmed_target(state):
        return False
    return should_ask("initial_contribution_amount", answers, 0.85)


def _should_ask_monthly_contribution(state: Dict[str, Any]) -> bool:
    answers = state.get("answers", {})
    if not _has_confirmed_target(state):
        return False
    return should_ask("monthly_contribution_amount", answers, 0.85)


def _funding_field_complete(answers: Dict[str, Any], field: str) -> bool:
    if not answers:
        return False
    item = answers.get(field) or {}
    value = item.get("value")
    confidence = float(item.get("confidence") or 0)
    if value is None or value == "":
        return False
    return confidence >= 0.85


def _update_funding_plan_status(session: Dict[str, Any]) -> None:
    answers = session.get("answers")
    if not answers:
        return
    initial_ok = _funding_field_complete(answers, "initial_contribution_amount")
    monthly_ok = _funding_field_complete(answers, "monthly_contribution_amount")
    status = "complete" if initial_ok and monthly_ok else "incomplete"
    answers["funding_plan_status"] = _answer_value(status, 1.0, "system_rule")


def _maybe_enter_funding_plan(session_id: str, session: Dict[str, Any], messages: list) -> Optional[StepResponse]:
    answers = session.get("answers", {})
    _update_funding_plan_status(session)
    if not _funding_field_complete(answers, "initial_contribution_amount"):
        return _ask_next(session_id, session, messages)
    if not _funding_field_complete(answers, "monthly_contribution_amount"):
        return _ask_next(session_id, session, messages)
    _update_funding_plan_status(session)
    return None


def _parse_amount_input(raw: str) -> Optional[float]:
    if not raw:
        return None
    cleaned = raw.lower()
    for token in ["€", "eur", "euros", "aed", "usd", "gbp"]:
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace(",", ".")
    multiplier = 1.0
    if cleaned.endswith("k"):
        multiplier = 1000.0
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def _parse_amount_with_currency(raw: str) -> tuple[Optional[float], Optional[str]]:
    if not raw:
        return None, None
    upper = raw.upper()
    currency = None
    for code in ["AED", "EUR", "USD", "GBP"]:
        if code in upper:
            currency = code
            break
    if "€" in raw and not currency:
        currency = "EUR"
    if "د.إ" in raw and not currency:
        currency = "AED"
    value = _parse_amount_input(raw)
    return value, currency


def _parse_horizon_to_months(value: Any) -> Optional[int]:
    raw = str(value or "").lower()
    if "short_term" in raw or "court" in raw:
        return 8
    if "mid_term" in raw or "1 à 3" in raw:
        return 24
    if "long_term" in raw or "3 à 5" in raw:
        return 48
    if "very_long" in raw or "au-delà" in raw:
        return 72
    if "mois" in raw:
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits:
            try:
                return int(digits)
            except ValueError:
                return None
    return None


def _store_contribution_amount(session: Dict[str, Any], field: str, raw: str) -> None:
    value, currency = _parse_amount_with_currency(raw)
    if value is None:
        if "answers" in session:
            session["answers"][field] = _answer_value(raw, 0.7, "user_text")
            session["answers"]["contribution_notes"] = _answer_value(raw, 0.7, "user_text")
    else:
        if "answers" in session:
            session["answers"][field] = _answer_value(value, 1.0, "user_text")
    if currency and "answers" in session:
        session["answers"]["contribution_currency"] = _answer_value(currency, 0.9, "inferred")
    _update_funding_plan_status(session)


def _ui_for_phase(phase: int) -> UIState:
    if phase == 0:
        return UIState(type="quick_replies", quick_replies=["On commence", "Plus tard"])
    if phase == 1:
        return UIState(type="free_text")
    if phase == 2:
        return UIState(type="quick_replies", quick_replies=quickRepliesByPhase(2), allow_free_text=True)
    if phase == 3:
        return UIState(type="quick_replies", quick_replies=quickRepliesByPhase(3), allow_free_text=True)
    if phase == 4:
        return UIState(
            type="quick_replies",
            quick_replies=[
                "Je veux éviter les variations, même si le rendement est plus modeste",
                "Je préfère un équilibre : un peu de variations, mais maîtrisées",
                "Je suis à l’aise avec des variations pour viser plus de performance",
                "Ça dépend : je veux que seule une partie soit plus dynamique",
            ],
        )
    if phase == 5:
        return UIState(
            type="quick_replies",
            quick_replies=[
                "Approche très sécurisée",
                "Approche équilibrée",
                "Approche optimisée sur la durée",
            ],
            allow_free_text=True,
        )
    if phase == 6:
        cards = [
            {"id": o["project_id"], "title": o["title"], "description": o["summary"]}
            for o in list_offers()
        ]
        return UIState(
            type="allocation_picker",
            allocation_picker={
                "min": 0,
                "max": 100,
                "step": 5,
                "max_total": EXCLUSIVE_TARGET_PCT,
                "cards": cards,
            },
            allow_free_text=False,
        )
    return UIState(type="free_text")


def quickRepliesByPhase(phase: int) -> list:
    if phase == 0:
        return ["On commence", "Plus tard"]
    if phase == 2:
        return ["J’ai un montant précis", "J’ai une idée approximative", "Je préfère avancer sans chiffre"]
    if phase == 3:
        return ["Accès à tout moment", "Occasionnellement", "Uniquement à l’échéance", "Pas besoin d’y toucher"]
    if phase == 6:
        return ["Oui", "Non", "Montre-moi les offres"]
    if phase == 7:
        return ["J'accepte", "Je refuse"]
    return []


def _progress(phase: int) -> Dict[str, int]:
    return {"phase": phase, "total_phases": TOTAL_PHASES}


def start_session(request: StartRequest) -> StartResponse:
    session_id = str(uuid.uuid4())
    state = {
        "phase": 0,
        "step_id": "welcome",
        "clarification_count": 0,
        "no_progress_count": 0,
        "exclusive_target_pct": EXCLUSIVE_TARGET_PCT,
        "allocations": {},
        "answers": _init_answers_state(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    STORE.set(session_id, state, DEFAULT_TTL_SECONDS)

    welcome = PHASE_PROMPTS[0]
    return StartResponse(
        session_id=session_id,
        messages=[Message(role="assistant", content=welcome)],
        ui=_ui_for_phase(0),
        progress=_progress(0),
        state=state,
    )


def step_session(request: StepRequest) -> StepResponse:
    session = STORE.get(request.session_id)
    if not session:
        raise ValueError("Session not found or expired")

    phase = session.get("phase", 0)
    step_id = session.get("step_id", "welcome")
    user_input = request.user_input
    input_type = user_input.type
    input_value = user_input.value
    input_text = str(input_value).strip() if input_value is not None else ""
    session["last_user_message"] = input_text

    messages: list[Message] = []

    # Phase 0: welcome -> move to phase 1 and ask for project if no input
    if phase == 0:
        if input_type != "single_choice":
            messages.append(Message(role="assistant", content="Merci de choisir une option pour continuer."))
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=_ui_for_phase(0),
                progress=_progress(0),
                state=session,
            )
        if input_text.lower().startswith("pas"):
            messages.append(Message(role="assistant", content="Pas de souci. Reviens quand tu seras prêt."))
            session["step_id"] = "welcome"
            session["updated_at"] = datetime.utcnow().isoformat()
            STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=_ui_for_phase(0),
                progress=_progress(0),
                state=session,
            )
        phase = 1
        step_id = "collect_project"
        session["step_id"] = step_id
        session["phase"] = phase
        return _ask_next(request.session_id, session, messages, input_text)

    # Phase 1: optional OpenAI clarification
    if phase == 1:
        clarification_count = session.get("clarification_count", 0)

        if step_id == "collect_project":
            if input_type != "free_text" or not input_text:
                return _ask_next(request.session_id, session, messages, input_text)
            if _is_vague_project_input(input_text):
                return _prompt_project_guidance(request.session_id, session, messages, input_text)
            session["project_text"] = input_text
            if "answers" in session:
                session["answers"]["project_summary"] = _answer_value(input_text, CONF_USER_TEXT, "user_text")
            _update_project_synthesis(session, input_text)
            session["step_id"] = "analyze"
            step_id = "analyze"

        if step_id == "analyze":
            if input_type == "free_text" and len(input_text) >= MIN_AI_TEXT_LEN:
                prefill = analyze_project_and_prefill(session.get("project_text", input_text))
                session["summary"] = prefill.project_summary.value or session.get("project_text", "")
                session["confidence"] = prefill.project_summary.confidence
                session["question"] = None
                session["prefill_notes"] = prefill.notes
                session["intent"] = prefill.intent.value
                session["intent_confidence"] = prefill.intent.confidence
                session["risk_profile_prefill"] = prefill.risk_profile.value
                session["risk_question_policy"] = prefill.risk_question_policy.value
                session["tone_guidance"] = prefill.tone_guidance.value
                if "answers" in session:
                    session["answers"]["project_summary"] = _answer_value(
                        prefill.project_summary.value or session.get("project_text", ""),
                        max(CONF_INFERRED, float(prefill.project_summary.confidence)),
                        "inferred",
                    )
                    if prefill.horizon.value:
                        session["answers"]["horizon"] = _answer_value(
                            prefill.horizon.value,
                            float(prefill.horizon.confidence),
                            "inferred",
                        )
                    if prefill.liquidity.value:
                        liquidity_label = _normalize_liquidity_label(prefill.liquidity.value)
                        session["answers"]["liquidity"] = _answer_value(
                            liquidity_label,
                            float(prefill.liquidity.confidence),
                            "inferred",
                        )
                        session["answers"]["liquidity_internal"] = _answer_value(
                            _liquidity_internal(liquidity_label),
                            float(prefill.liquidity.confidence),
                            "inferred",
                        )
                    if prefill.risk_profile.value:
                        session["answers"]["risk"] = _answer_value(
                            {"profile": prefill.risk_profile.value},
                            float(prefill.risk_profile.confidence),
                            "inferred",
                        )
                    if prefill.risk_question_policy.value:
                        session["answers"]["risk_question_policy"] = _answer_value(
                            prefill.risk_question_policy.value,
                            float(prefill.risk_question_policy.confidence),
                            "inferred",
                        )
                    if prefill.tone_guidance.value:
                        session["answers"]["tone_style"] = _answer_value(
                            prefill.tone_guidance.value,
                            float(prefill.tone_guidance.confidence),
                            "inferred",
                        )
                    if prefill.target_amount.value is not None:
                        session["answers"]["target_amount"] = _answer_value(
                            prefill.target_amount.value,
                            float(prefill.target_amount.confidence),
                            "inferred",
                        )
                    if prefill.target_amount_type.value:
                        session["answers"]["target_amount_type"] = _answer_value(
                            prefill.target_amount_type.value,
                            float(prefill.target_amount_type.confidence),
                            "inferred",
                        )
                    if prefill.initial_contribution_amount.value is not None:
                        session["answers"]["initial_contribution_amount"] = _answer_value(
                            prefill.initial_contribution_amount.value,
                            float(prefill.initial_contribution_amount.confidence),
                            "inferred",
                        )
                    if prefill.monthly_contribution_amount.value is not None:
                        session["answers"]["monthly_contribution_amount"] = _answer_value(
                            prefill.monthly_contribution_amount.value,
                            float(prefill.monthly_contribution_amount.confidence),
                            "inferred",
                        )
                    if prefill.contribution_currency.value:
                        session["answers"]["contribution_currency"] = _answer_value(
                            prefill.contribution_currency.value,
                            float(prefill.contribution_currency.confidence),
                            "inferred",
                        )
                    if prefill.contribution_notes.value:
                        session["answers"]["contribution_notes"] = _answer_value(
                            prefill.contribution_notes.value,
                            float(prefill.contribution_notes.confidence),
                            "inferred",
                        )
                    if prefill.recurring_saving.value:
                        session["answers"]["recurring_saving"] = _answer_value(
                            prefill.recurring_saving.value,
                            float(prefill.recurring_saving.confidence),
                            "inferred",
                        )
                    if prefill.recurring_amount.value is not None:
                        session["answers"]["recurring_amount"] = _answer_value(
                            prefill.recurring_amount.value,
                            float(prefill.recurring_amount.confidence),
                            "inferred",
                        )
                _update_project_synthesis(session, session.get("summary") or input_text)
                session["tone_style"] = detect_tone_style(session)
                if "answers" in session:
                    session["answers"]["tone_style"] = _answer_value(session["tone_style"], CONF_INFERRED, "inferred")
                _update_funding_plan_status(session)

                if session.get("confidence", 1.0) < CONFIDENCE_THRESHOLD or session.get("question"):
                    session["clarification_count"] = clarification_count + 1
                    session["question"] = None
                    return _prompt_project_guidance(request.session_id, session, messages, input_text)

                _maybe_append_micro_feedback(session, messages, input_text)
                messages.append(Message(role="assistant", content=f"Je pense avoir bien compris : {session['summary']}. Parfait — avançons."))
                return _continue_after_project_summary(request.session_id, session, messages)
            return _help_user_clarify_project(request.session_id, session, input_text)

        if step_id == "clarify_project":
            if input_type != "free_text" or not input_text:
                return _prompt_project_guidance(request.session_id, session, messages, input_text)
            if _is_vague_project_input(input_text):
                return _prompt_project_guidance(request.session_id, session, messages, input_text)
            session["project_text"] = f"{session.get('project_text', '')}\nClarification: {input_text}".strip()
            prefill = analyze_project_and_prefill(session["project_text"])
            session["summary"] = prefill.project_summary.value or session.get("project_text", "")
            session["confidence"] = prefill.project_summary.confidence
            session["question"] = prefill.notes
            session["prefill_notes"] = prefill.notes
            session["intent"] = prefill.intent.value
            session["intent_confidence"] = prefill.intent.confidence
            session["risk_profile_prefill"] = prefill.risk_profile.value
            session["risk_question_policy"] = prefill.risk_question_policy.value
            session["tone_guidance"] = prefill.tone_guidance.value
            if "answers" in session:
                session["answers"]["project_summary"] = _answer_value(
                    prefill.project_summary.value or session.get("project_text", ""),
                    max(CONF_INFERRED, float(prefill.project_summary.confidence)),
                    "inferred",
                )
                if prefill.horizon.value:
                    session["answers"]["horizon"] = _answer_value(
                        prefill.horizon.value,
                        float(prefill.horizon.confidence),
                        "inferred",
                    )
                if prefill.liquidity.value:
                    liquidity_label = _normalize_liquidity_label(prefill.liquidity.value)
                    session["answers"]["liquidity"] = _answer_value(
                        liquidity_label,
                        float(prefill.liquidity.confidence),
                        "inferred",
                    )
                    session["answers"]["liquidity_internal"] = _answer_value(
                        _liquidity_internal(liquidity_label),
                        float(prefill.liquidity.confidence),
                        "inferred",
                    )
                if prefill.risk_profile.value:
                    session["answers"]["risk"] = _answer_value(
                        {"profile": prefill.risk_profile.value},
                        float(prefill.risk_profile.confidence),
                        "inferred",
                    )
                if prefill.risk_question_policy.value:
                    session["answers"]["risk_question_policy"] = _answer_value(
                        prefill.risk_question_policy.value,
                        float(prefill.risk_question_policy.confidence),
                        "inferred",
                    )
                if prefill.tone_guidance.value:
                    session["answers"]["tone_style"] = _answer_value(
                        prefill.tone_guidance.value,
                        float(prefill.tone_guidance.confidence),
                        "inferred",
                    )
                if prefill.target_amount.value is not None:
                    session["answers"]["target_amount"] = _answer_value(
                        prefill.target_amount.value,
                        float(prefill.target_amount.confidence),
                        "inferred",
                    )
                if prefill.target_amount_type.value:
                    session["answers"]["target_amount_type"] = _answer_value(
                        prefill.target_amount_type.value,
                        float(prefill.target_amount_type.confidence),
                        "inferred",
                    )
                if prefill.initial_contribution_amount.value is not None:
                    session["answers"]["initial_contribution_amount"] = _answer_value(
                        prefill.initial_contribution_amount.value,
                        float(prefill.initial_contribution_amount.confidence),
                        "inferred",
                    )
                if prefill.monthly_contribution_amount.value is not None:
                    session["answers"]["monthly_contribution_amount"] = _answer_value(
                        prefill.monthly_contribution_amount.value,
                        float(prefill.monthly_contribution_amount.confidence),
                        "inferred",
                    )
                if prefill.contribution_currency.value:
                    session["answers"]["contribution_currency"] = _answer_value(
                        prefill.contribution_currency.value,
                        float(prefill.contribution_currency.confidence),
                        "inferred",
                    )
                if prefill.contribution_notes.value:
                    session["answers"]["contribution_notes"] = _answer_value(
                        prefill.contribution_notes.value,
                        float(prefill.contribution_notes.confidence),
                        "inferred",
                    )
                if prefill.recurring_saving.value:
                    session["answers"]["recurring_saving"] = _answer_value(
                        prefill.recurring_saving.value,
                        float(prefill.recurring_saving.confidence),
                        "inferred",
                    )
                if prefill.recurring_amount.value is not None:
                    session["answers"]["recurring_amount"] = _answer_value(
                        prefill.recurring_amount.value,
                        float(prefill.recurring_amount.confidence),
                        "inferred",
                    )
            session["tone_style"] = detect_tone_style(session)
            if "answers" in session:
                session["answers"]["tone_style"] = _answer_value(session["tone_style"], CONF_INFERRED, "inferred")
            _update_funding_plan_status(session)

            if session.get("confidence", 1.0) < CONFIDENCE_THRESHOLD and session.get("question") and clarification_count < MAX_CLARIFICATIONS:
                session["clarification_count"] = clarification_count + 1
                question = session.get("question") or "Peux-tu préciser ton projet en une phrase ?"
                messages.append(Message(role="assistant", content=question))
                session["updated_at"] = datetime.utcnow().isoformat()
                STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=_ui_for_phase(1),
                    progress=_progress(1),
                    state=session,
                )

            _maybe_append_micro_feedback(session, messages, input_text)
            messages.append(Message(role="assistant", content=f"Je pense avoir bien compris : {session['summary']}. Parfait — avançons."))
            return _continue_after_project_summary(request.session_id, session, messages)

        if step_id == "project_hint":
            if input_type != "single_choice" or not input_text:
                return _prompt_project_guidance(request.session_id, session, messages, input_text)
            _apply_project_hint_choice(input_text, session)
            if not session.get("summary"):
                return _prompt_project_guidance(request.session_id, session, messages, input_text)
            _maybe_append_micro_feedback(session, messages, input_text)
            messages.append(Message(role="assistant", content=f"Je pense avoir bien compris : {session['summary']}. Parfait — avançons."))
            return _continue_after_project_summary(request.session_id, session, messages)

        if step_id in ("clarify_intent", "collect_budget", "collect_horizon", "offer_vault", "recap"):
            if not input_text:
                return _ask_next(request.session_id, session, messages, input_text)
            if step_id == "clarify_intent":
                _apply_project_hint_choice(input_text, session)
                if not session.get("summary"):
                    session["summary"] = input_text
                    if "answers" in session:
                        session["answers"]["project_summary"] = _answer_value(input_text, CONF_USER_TEXT, "user_text")
                _update_project_synthesis(session, session.get("summary") or input_text)
                _maybe_append_micro_feedback(session, messages, input_text)
                return _ask_next(request.session_id, session, messages, input_text)
            if step_id == "collect_budget":
                if not should_ask("target_amount", session.get("answers", {})):
                    return _skip_question(request.session_id, session, messages, "target_amount", input_text)
                interpretation = _try_interpret_answer(
                    request.session_id,
                    session,
                    messages,
                    step_id,
                    "Tu as une idée du budget, même approximative ?",
                    "target_amount",
                    input_text,
                )
                if interpretation is None:
                    parsed = _parse_amount_input(input_text)
                    if parsed is not None and "answers" in session:
                        session["answers"]["target_amount"] = _answer_value(parsed, 1.0, "user_text")
                        session["answers"]["target_amount_type"] = _answer_value("exact", 1.0, "user_text")
                _maybe_append_micro_feedback(session, messages, input_text)
                return _ask_next(request.session_id, session, messages, input_text)
            if step_id == "collect_horizon":
                if not should_ask("horizon", session.get("answers", {}), 0.75):
                    return _skip_question(request.session_id, session, messages, "horizon", input_text)
                if "answers" in session:
                    session["answers"]["horizon"] = _answer_value(input_text, 1.0, "user_text")
                _maybe_append_micro_feedback(session, messages, input_text)
                return _ask_next(request.session_id, session, messages, input_text)
            if step_id == "offer_vault":
                lower = input_text.lower()
                session["vault_offer_done"] = True
                if any(token in lower for token in ["oui", "ok", "go", "vas-y"]):
                    session["vault_opt_in"] = True
                    messages.append(Message(role="assistant", content="Parfait, on crée ce coffre ensemble."))
                else:
                    messages.append(Message(role="assistant", content="OK, on avance sans forcer."))
                return _ask_next(request.session_id, session, messages, input_text)
            if step_id == "recap":
                session["recap_done"] = True
                messages.append(Message(role="assistant", content="Merci, je note."))
                return _ask_next(request.session_id, session, messages, input_text)

    # Phase 2: ambition chiffrée + récurrence
    elif phase == 2:
        if step_id == "funding_initial":
            if not should_ask("initial_contribution_amount", session.get("answers", {})):
                return _skip_question(request.session_id, session, messages, "initial_contribution_amount", input_text)
            if input_type != "free_text" or not input_text:
                return _ask_next(request.session_id, session, messages, input_text)
            interpretation = _try_interpret_answer(
                request.session_id,
                session,
                messages,
                step_id,
                PHASE_2_INITIAL_CONTRIBUTION_PROMPT,
                "initial_contribution_amount",
                input_text,
            )
            if interpretation and interpretation.next:
                session["debug_interpretation_next"] = interpretation.next.question
            if interpretation is None:
                _store_contribution_amount(session, "initial_contribution_amount", input_text)
            _maybe_append_micro_feedback(session, messages, input_text)
            return _ask_next(request.session_id, session, messages, input_text)

        if step_id == "funding_monthly":
            if not should_ask("monthly_contribution_amount", session.get("answers", {})):
                return _skip_question(request.session_id, session, messages, "monthly_contribution_amount", input_text)
            if input_type != "free_text" or not input_text:
                return _ask_next(request.session_id, session, messages, input_text)
            interpretation = _try_interpret_answer(
                request.session_id,
                session,
                messages,
                step_id,
                PHASE_2_MONTHLY_CONTRIBUTION_PROMPT,
                "monthly_contribution_amount",
                input_text,
            )
            if interpretation and interpretation.next:
                session["debug_interpretation_next"] = interpretation.next.question
            if interpretation is None:
                _store_contribution_amount(session, "monthly_contribution_amount", input_text)
            _infer_savings_rhythm_from_amount(session)
            _maybe_append_micro_feedback(session, messages, input_text)
            mission = _maybe_send_mission_statement(request.session_id, session, messages)
            if mission:
                return mission
            return _ask_next(request.session_id, session, messages, input_text)
        if step_id == "phase_2_initial_contribution":
            if not should_ask("initial_contribution_amount", session.get("answers", {})):
                return _skip_question(request.session_id, session, messages, "initial_contribution_amount", input_text)
            if input_type != "free_text" or not input_text:
                return _ask_next(request.session_id, session, messages, input_text)
            _store_contribution_amount(session, "initial_contribution_amount", input_text)
            _maybe_append_micro_feedback(session, messages, input_text)
            if _should_ask_monthly_contribution(session):
                return _ask_next(request.session_id, session, messages, input_text)
            if _should_ask_recurring(session):
                session["step_id"] = "phase_2_recurring"
                message = _render_assistant_message(
                    "phase_2_recurring",
                    session,
                    PHASE_2_RECURRING_PROMPT,
                    ["Mettre de côté régulièrement", "Quand c’est possible", "Un mélange des deux"],
                )
                messages.append(Message(role="assistant", content=message))
                session["updated_at"] = datetime.utcnow().isoformat()
                STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=UIState(
                        type="quick_replies",
                        quick_replies=["Mettre de côté régulièrement", "Quand c’est possible", "Un mélange des deux"],
                        allow_free_text=True,
                    ),
                    progress=_progress(2),
                    state=session,
                )
            _maybe_append_indicative_calc(session, messages)
            return _ask_next(request.session_id, session, messages, input_text)

        if step_id == "phase_2_monthly_contribution":
            if not should_ask("monthly_contribution_amount", session.get("answers", {})):
                return _skip_question(request.session_id, session, messages, "monthly_contribution_amount", input_text)
            if input_type != "free_text" or not input_text:
                return _ask_next(request.session_id, session, messages, input_text)
            _store_contribution_amount(session, "monthly_contribution_amount", input_text)
            _infer_savings_rhythm_from_amount(session)
            _maybe_append_micro_feedback(session, messages, input_text)
            mission = _maybe_send_mission_statement(request.session_id, session, messages)
            if mission:
                return mission
            if _should_ask_recurring(session):
                return _ask_next(request.session_id, session, messages, input_text)
            _maybe_append_indicative_calc(session, messages)
            return _ask_next(request.session_id, session, messages, input_text)
        if step_id == "phase_2_amount_type":
            if input_type == "free_text" and input_text:
                raw = input_text.strip()
                lower = raw.lower()
                if "-" in raw or "–" in raw or "entre" in lower:
                    amount_value = raw
                    amount_type = "range"
                else:
                    parsed = _parse_amount_input(raw)
                    amount_value = parsed if parsed is not None else raw
                    amount_type = "exact" if parsed is not None else "range"
                session["target_amount"] = amount_value
                if "answers" in session:
                    session["answers"]["target_amount"] = _answer_value(amount_value, 1.0, "user_text")
                    session["answers"]["target_amount_type"] = _answer_value(amount_type, 1.0, "user_text")
                _maybe_append_micro_feedback(session, messages, input_text)
                mission = _maybe_send_mission_statement(request.session_id, session, messages)
                if mission:
                    return mission
                if _should_ask_initial_contribution(session):
                    return _ask_next(request.session_id, session, messages, input_text)
                if _should_ask_recurring(session):
                    return _ask_next(request.session_id, session, messages, input_text)
                    session["updated_at"] = datetime.utcnow().isoformat()
                    STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                    return StepResponse(
                        session_id=request.session_id,
                        messages=messages,
                        ui=UIState(
                            type="quick_replies",
                            quick_replies=["Mettre de côté régulièrement", "Quand c’est possible", "Un mélange des deux"],
                            allow_free_text=True,
                        ),
                        progress=_progress(2),
                        state=session,
                    )
                session["step_id"] = "phase_3"
                phase = 3
                _maybe_append_indicative_calc(session, messages)
                message = _render_assistant_message(
                    "phase_3",
                    session,
                    _phase3_prompt(session),
                    ["Accès à tout moment", "Occasionnellement", "Uniquement à l’échéance", "Pas besoin d’y toucher"],
                )
                messages.append(Message(role="assistant", content=message))
                session["phase"] = phase
                session["updated_at"] = datetime.utcnow().isoformat()
                STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=_ui_for_phase(3),
                    progress=_progress(3),
                    state=session,
                )
            if input_type != "single_choice":
                message = _render_assistant_message(
                    "phase_2_amount_type",
                    session,
                    PHASE_PROMPTS[2],
                    ["J’ai un montant précis", "J’ai une idée approximative", "Je préfère avancer sans chiffre"],
                )
                messages.append(Message(role="assistant", content=message))
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=_ui_for_phase(2),
                    progress=_progress(2),
                    state=session,
                )
            choice = input_text.lower()
            if "montant précis" in choice:
                session["target_amount_type"] = "exact"
                if "answers" in session:
                    session["answers"]["target_amount_type"] = _answer_value("exact", 1.0, "user_choice")
                return _ask_next(request.session_id, session, messages, input_text)
            if "idée approximative" in choice:
                session["target_amount_type"] = "range"
                if "answers" in session:
                    session["answers"]["target_amount_type"] = _answer_value("range", 1.0, "user_choice")
                return _ask_next(request.session_id, session, messages, input_text)
            session["target_amount_type"] = "none"
            if "answers" in session:
                session["answers"]["target_amount_type"] = _answer_value("none", 1.0, "user_choice")
                session["answers"]["target_amount"] = _answer_value(None, 1.0, "user_choice")
            _maybe_append_micro_feedback(session, messages, input_text)

            if _should_ask_recurring(session):
                session["step_id"] = "phase_2_recurring"
                message = _render_assistant_message(
                    "phase_2_recurring",
                    session,
                    PHASE_2_RECURRING_PROMPT,
                    ["Mettre de côté régulièrement", "Quand c’est possible", "Un mélange des deux"],
                )
                messages.append(Message(role="assistant", content=message))
                return _ask_next(request.session_id, session, messages, input_text)

            _maybe_append_indicative_calc(session, messages)
            return _ask_next(request.session_id, session, messages, input_text)

        if step_id == "phase_2_amount_value":
            if not should_ask("target_amount", session.get("answers", {})):
                return _skip_question(request.session_id, session, messages, "target_amount", input_text)
            amount_type = (session.get("target_amount_type") or (session.get("answers", {}).get("target_amount_type") or {}).get("value")) or "exact"
            prompt = PHASE_2_AMOUNT_EXACT_PROMPT if amount_type == "exact" else PHASE_2_AMOUNT_RANGE_PROMPT
            if input_type != "free_text" or not input_text:
                return _ask_next(request.session_id, session, messages, input_text)
            interpretation = _try_interpret_answer(
                request.session_id,
                session,
                messages,
                step_id,
                prompt,
                "target_amount",
                input_text,
            )
            if interpretation and interpretation.next:
                session["debug_interpretation_next"] = interpretation.next.question
            if interpretation is None:
                if amount_type == "range":
                    amount_value = input_text
                else:
                    parsed = _parse_amount_input(input_text)
                    amount_value = parsed if parsed is not None else input_text
                session["target_amount"] = amount_value
                if "answers" in session:
                    session["answers"]["target_amount"] = _answer_value(amount_value, 1.0, "user_text")
            _maybe_append_micro_feedback(session, messages, input_text)
            mission = _maybe_send_mission_statement(request.session_id, session, messages)
            if mission:
                return mission
            return _ask_next(request.session_id, session, messages, input_text)

        if step_id == "phase_2_recurring":
            if input_type != "single_choice":
                return _ask_next(request.session_id, session, messages, input_text)
            if "régulièrement" in input_text.lower():
                recurring_value = "regular"
            elif "mélange" in input_text.lower():
                recurring_value = "mixed"
            else:
                recurring_value = "sometimes"
            session["recurring_saving"] = recurring_value
            if "answers" in session:
                session["answers"]["recurring_saving"] = _answer_value(recurring_value, 1.0, "user_choice")
            _maybe_append_micro_feedback(session, messages, input_text)

            session["step_id"] = "phase_3"
            phase = 3
            _maybe_append_indicative_calc(session, messages)
            message = _render_assistant_message(
                "phase_3",
                session,
                _phase3_prompt(session),
                ["Accès à tout moment", "Occasionnellement", "Uniquement à l’échéance", "Pas besoin d’y toucher"],
            )
            messages.append(Message(role="assistant", content=message))
            session["phase"] = phase
            session["updated_at"] = datetime.utcnow().isoformat()
            STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=_ui_for_phase(3),
                progress=_progress(3),
                state=session,
            )

        return _ask_next(request.session_id, session, messages, input_text)

    # Phase 3: liquidity
    elif phase == 3:
        if step_id == "phase_3_savings_rhythm":
            if input_type != "single_choice":
                return _ask_next(request.session_id, session, messages, input_text)
            choice = input_text.lower()
            if "réguli" in choice:
                rhythm_value = "regular"
            elif "ponctu" in choice:
                rhythm_value = "sometimes"
            elif "mélange" in choice:
                rhythm_value = "mixed"
            else:
                rhythm_value = "later"
            if "answers" in session:
                session["answers"]["savings_rhythm"] = _answer_value(rhythm_value, 1.0, "user_choice")
            _maybe_append_micro_feedback(session, messages, input_text)
            return _ask_next(request.session_id, session, messages, input_text)
        if not should_ask("liquidity", session.get("answers", {}), 0.75):
            liquidity_value = session["answers"]["liquidity"]["value"]
            liquidity_label = _normalize_liquidity_label(liquidity_value)
            session["liquidity"] = liquidity_label
            if "answers" in session:
                session["answers"]["liquidity"] = _answer_value(liquidity_label, 1.0, "user_choice")
                session["answers"]["liquidity_internal"] = _answer_value(
                    _liquidity_internal(liquidity_label),
                    1.0,
                    "user_choice",
                )
            session["debug_liquidity_raw_value"] = liquidity_value
            session["debug_liquidity_label_used"] = liquidity_label
            messages.append(Message(role="assistant", content=_liquidity_ack(liquidity_label)))
            _infer_savings_rhythm_from_amount(session)
            return _ask_next(request.session_id, session, messages, input_text)
        liquidity_label = _normalize_liquidity_label(input_text)
        session["liquidity"] = liquidity_label
        session["tone_style"] = detect_tone_style(session)
        if "answers" in session:
            session["answers"]["liquidity"] = _answer_value(liquidity_label, 1.0, "user_choice")
            session["answers"]["liquidity_internal"] = _answer_value(
                _liquidity_internal(liquidity_label),
                1.0,
                "user_choice",
            )
            session["answers"]["tone_style"] = _answer_value(session["tone_style"], CONF_INFERRED, "inferred")
        session["debug_liquidity_raw_value"] = input_text
        session["debug_liquidity_label_used"] = liquidity_label
        _maybe_append_micro_feedback(session, messages, input_text)
        messages.append(Message(role="assistant", content=_liquidity_ack(liquidity_label)))
        _infer_savings_rhythm_from_amount(session)
        return _ask_next(request.session_id, session, messages, input_text)

    # Phase 4: risk behavior
    elif phase == 4:
        policy, policy_source = _risk_policy(session)
        session["debug_entered_phase"] = 4
        session["debug_risk_policy_used"] = policy
        session["debug_risk_policy_source"] = policy_source
        if policy == "skip":
            session["debug_generated_risk_question"] = False
            return _advance_to_phase5_after_risk_skip(request.session_id, session, messages)

        if not should_ask("risk", session.get("answers", {}), 0.75):
            risk_value = session["answers"]["risk"]["value"]
            if isinstance(risk_value, dict):
                session["risk_profile"] = risk_value.get("profile")
                session["risk_score"] = risk_value.get("score")
                session["risk_behavior"] = risk_value.get("choice")
            session["debug_generated_risk_question"] = False
            messages.append(Message(role="assistant", content=_transition_message("risk", None)))
            session["step_id"] = "phase_5"
            phase = 5
            message = _render_assistant_message(
                "phase_5",
                session,
                _phase5_prompt(session),
                _phase5_options(session),
            )
            messages.append(Message(role="assistant", content=message))
            session["phase"] = phase
            session["updated_at"] = datetime.utcnow().isoformat()
            STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=_ui_for_phase(5),
                progress=_progress(5),
                state=session,
            )
        if input_type != "single_choice":
            session["debug_generated_risk_question"] = True
            message = _render_assistant_message(
                "phase_4",
                session,
                PHASE_PROMPTS[4],
                _risk_options(policy),
            )
            messages.append(Message(role="assistant", content=message))
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=UIState(type="quick_replies", quick_replies=_risk_options(policy)),
                progress=_progress(4),
                state=session,
            )
        mapped = _map_risk_choice(input_text, policy)
        risk_profile = mapped.get("profile")
        risk_score = mapped.get("score")
        session["risk_profile"] = risk_profile
        session["risk_score"] = risk_score
        session["risk_behavior"] = input_text
        session["tone_style"] = detect_tone_style(session)
        if "answers" in session:
            session["answers"]["risk"] = _answer_value(
                {"profile": risk_profile, "score": risk_score, "choice": input_text},
                1.0,
                "user_choice",
            )
            session["answers"]["tone_style"] = _answer_value(session["tone_style"], CONF_INFERRED, "inferred")
        _maybe_append_micro_feedback(session, messages, input_text)
        return _ask_next(request.session_id, session, messages, input_text)

    # Phase 5: strategy construction
    elif phase == 5:
        if step_id == "phase_5_target_amount":
            if not should_ask("target_amount", session.get("answers", {})):
                return _skip_question(request.session_id, session, messages, "target_amount", input_text)
            if input_type != "free_text" or not input_text:
                return _ask_next(request.session_id, session, messages, input_text)
            interpretation = _try_interpret_answer(
                request.session_id,
                session,
                messages,
                step_id,
                PHASE_5_TARGET_AMOUNT_PROMPT,
                "target_amount",
                input_text,
            )
            if interpretation and interpretation.next:
                session["debug_interpretation_next"] = interpretation.next.question
            if interpretation is None:
                raw = input_text.strip()
                lower = raw.lower()
                if any(token in lower for token in ["plus possible", "le plus possible", "sans", "pas", "aucun"]):
                    target_value = None
                    target_type = "none"
                elif "-" in raw or "–" in raw or "entre" in lower:
                    target_value = raw
                    target_type = "range"
                else:
                    parsed = _parse_amount_input(raw)
                    target_value = parsed if parsed is not None else raw
                    target_type = "exact" if parsed is not None else "range"
                if "answers" in session:
                    session["answers"]["target_amount"] = _answer_value(target_value, 1.0, "user_choice")
                    session["answers"]["target_amount_type"] = _answer_value(target_type, 1.0, "user_choice")
            _maybe_append_micro_feedback(session, messages, input_text)
            return _ask_next(request.session_id, session, messages, input_text)

        if step_id == "phase_5_savings_rhythm":
            if input_type != "single_choice":
                return _ask_next(request.session_id, session, messages, input_text)
            choice = input_text.lower()
            if "réguli" in choice:
                rhythm_value = "regular"
            elif "ponctu" in choice:
                rhythm_value = "sometimes"
            elif "mélange" in choice:
                rhythm_value = "mixed"
            else:
                rhythm_value = "later"
            if "answers" in session:
                session["answers"]["savings_rhythm"] = _answer_value(rhythm_value, 1.0, "user_choice")
            _maybe_append_micro_feedback(session, messages, input_text)

            session["step_id"] = "phase_5"
            message = _render_assistant_message(
                "phase_5",
                session,
                _phase5_prompt(session),
                _phase5_options(session),
            )
            messages.append(Message(role="assistant", content=message))
            session["updated_at"] = datetime.utcnow().isoformat()
            STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=_ui_for_phase(5),
                progress=_progress(5),
                state=session,
            )

        if step_id == "phase_5":
            if _should_ask_target_amount(session):
                return _ask_next(request.session_id, session, messages, input_text)
            if _should_ask_savings_rhythm(session):
                return _ask_next(request.session_id, session, messages, input_text)
        if not should_ask("strategy_preference", session.get("answers", {}), 0.7):
            strategy_value = session["answers"]["strategy_preference"]["value"]
            session["strategy_construction"] = strategy_value
            messages.append(Message(role="assistant", content=_transition_message("strategy_preference", None)))
            if _is_short_term_horizon(session):
                if "answers" in session:
                    session["answers"]["exclusives_opt_in"] = _answer_value(
                        False,
                        1.0,
                        "system_rule",
                    )
                messages.append(Message(
                    role="assistant",
                    content="Pour un objectif à moins d’un an, on privilégie des solutions simples et liquides plutôt que des projets immobilisés."
                ))
                session["step_id"] = "phase_7"
                phase = 7
                if not session.get("phase7_recap"):
                    tone_style = session.get("tone_style") or detect_tone_style(session)
                    session["tone_style"] = tone_style
                    recap = compose_final_advisor_recap(session.get("answers", {}), tone_style)
                    session["phase7_recap"] = recap.model_dump()
                messages.append(Message(role="assistant", content=_format_phase7_recap(session["phase7_recap"])))
                session["step_id"] = "phase_7_next"
                session["phase"] = phase
                session["updated_at"] = datetime.utcnow().isoformat()
                STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=UIState(
                        type="quick_replies",
                        quick_replies=(session.get("phase7_recap") or {}).get(
                            "next_steps",
                            ["Activer cette stratégie", "Revoir un point"],
                        ),
                    ),
                    progress=_progress(7),
                    state=session,
                )
            session["step_id"] = "exclusive_allocations"
            phase = 6
            messages.append(Message(role="assistant", content=f"{PHASE_PROMPTS[6]}\n\n{_build_offers_text_for_state(session)}"))
            session["phase"] = phase
            session["updated_at"] = datetime.utcnow().isoformat()
            STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=_allocation_ui_for_state(session),
                progress=_progress(6),
                state=session,
            )
        if input_type != "single_choice":
            message = _render_assistant_message(
                "phase_5",
                session,
                _phase5_prompt(session),
                _phase5_options(session),
            )
            messages.append(Message(role="assistant", content=message))
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=_ui_for_phase(5),
                progress=_progress(5),
                state=session,
            )
        choice_map = {
            "Approche très sécurisée": "secure",
            "Approche équilibrée": "balanced",
            "Approche optimisée sur la durée": "optimized",
        }
        session["strategy_construction"] = choice_map.get(input_text, "balanced")
        if "answers" in session:
            session["answers"]["strategy_preference"] = _answer_value(
                session["strategy_construction"],
                1.0,
                "user_choice",
            )
        _maybe_append_micro_feedback(session, messages, input_text)
        return _ask_next(request.session_id, session, messages, input_text)
        session["step_id"] = "exclusive_allocations"
        phase = 6
        messages.append(Message(role="assistant", content=f"{PHASE_PROMPTS[6]}\n\n{_build_offers_text_for_state(session)}"))
        session["phase"] = phase
        session["updated_at"] = datetime.utcnow().isoformat()
        STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
        return StepResponse(
            session_id=request.session_id,
            messages=messages,
            ui=_allocation_ui_for_state(session),
            progress=_progress(6),
            state=session,
        )

    # Phase 6: exclusive offers selection
    elif phase == 6:
        if step_id == "exclusive_consent":
            if input_type != "single_choice":
                messages.append(Message(role="assistant", content="Merci de confirmer ou refuser."))
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=UIState(type="quick_replies", quick_replies=["J'accepte", "Je refuse"]),
                    progress=_progress(6),
                    state=session,
                )
            session["exclusive_offers_choice"] = input_text
            if "answers" in session:
                session["answers"]["exclusives_opt_in"] = _answer_value(
                    input_text,
                    1.0,
                    "user_choice",
                )
            session["step_id"] = "phase_7"
            phase = 7
            if not session.get("phase7_recap"):
                tone_style = session.get("tone_style") or detect_tone_style(session)
                session["tone_style"] = tone_style
                recap = compose_final_advisor_recap(session.get("answers", {}), tone_style)
                session["phase7_recap"] = recap.model_dump()
            messages.append(Message(role="assistant", content=_format_phase7_recap(session["phase7_recap"])))
            session["step_id"] = "phase_7_next"
            session["phase"] = phase
            session["updated_at"] = datetime.utcnow().isoformat()
            STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=UIState(
                    type="quick_replies",
                    quick_replies=(session.get("phase7_recap") or {}).get(
                        "next_steps",
                        ["Activer cette stratégie", "Revoir un point"],
                    ),
                ),
                progress=_progress(7),
                state=session,
            )
        else:
            # Allocation picker input
            if input_type != "allocation":
                messages.append(Message(role="assistant", content="Merci de proposer une allocation."))
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=_ui_for_phase(6),
                    progress=_progress(6),
                    state=session,
                )
            allocations = session.get("allocations", {})
            project_id = (input_value or {}).get("project_id")
            percent = (input_value or {}).get("percent")
            if project_id and percent is not None:
                allocations[project_id] = percent
            total_pct = sum(allocations.values())
            if total_pct > session.get("exclusive_target_pct", EXCLUSIVE_TARGET_PCT):
                messages.append(Message(
                    role="assistant",
                    content=f"Allocation trop élevée ({total_pct}%). Max {session.get('exclusive_target_pct', EXCLUSIVE_TARGET_PCT)}%."
                ))
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=_allocation_ui_for_state(session),
                    progress=_progress(6),
                    state=session,
                )
            session["allocations"] = allocations
            if "answers" in session:
                session["answers"]["exclusives_allocations"] = _answer_value(
                    allocations,
                    1.0,
                    "user_choice",
                )
            session["step_id"] = "exclusive_consent"
            messages.append(Message(role="assistant", content="Souhaites-tu confirmer ces allocations ?"))
            session["updated_at"] = datetime.utcnow().isoformat()
            STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=UIState(type="quick_replies", quick_replies=["J'accepte", "Je refuse"]),
                progress=_progress(6),
                state=session,
            )

    # Phase 7: completed
    else:
        if step_id == "phase_7_next":
            if input_type != "single_choice":
                tone_style = session.get("tone_style") or detect_tone_style(session)
                session["tone_style"] = tone_style
                messages.append(Message(role="assistant", content=_phase7_next_message(tone_style)))
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=UIState(
                        type="quick_replies",
                        quick_replies=["Activer cette stratégie", "Revoir un point"],
                    ),
                    progress=_progress(7),
                    state=session,
                )
            if input_text.lower().startswith("revoir"):
                session["step_id"] = "phase_7_review_menu"
                messages.append(Message(role="assistant", content="Quel point souhaites-tu revoir ?"))
                session["updated_at"] = datetime.utcnow().isoformat()
                STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=UIState(
                        type="quick_replies",
                        quick_replies=["Cap chiffré", "Disponibilité", "Confort face aux variations", "Offres exclusives"],
                    ),
                    progress=_progress(7),
                    state=session,
                )
            session["activated"] = True
            tone_style = session.get("tone_style") or detect_tone_style(session)
            session["tone_style"] = tone_style
            messages.append(Message(role="assistant", content=_phase7_activation_message(tone_style)))
            session["updated_at"] = datetime.utcnow().isoformat()
            STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
            return StepResponse(
                session_id=request.session_id,
                messages=messages,
                ui=UIState(type="quick_replies", quick_replies=["Revoir un point"]),
                progress=_progress(7),
                state=session,
            )

        if step_id == "phase_7_review_menu":
            if input_type != "single_choice":
                messages.append(Message(role="assistant", content="Quel point souhaites-tu revoir ?"))
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=UIState(
                        type="quick_replies",
                        quick_replies=["Cap chiffré", "Disponibilité", "Confort face aux variations", "Offres exclusives"],
                    ),
                    progress=_progress(7),
                    state=session,
                )
            choice = input_text.lower()
            if "cap" in choice or "chiffr" in choice:
                session["phase"] = 2
                session["step_id"] = "phase_2_amount_type"
                message = _render_assistant_message(
                    "phase_2_amount_type",
                    session,
                    PHASE_PROMPTS[2],
                    ["J’ai un montant précis", "J’ai une idée approximative", "Je préfère avancer sans chiffre"],
                )
                messages.append(Message(role="assistant", content=message))
                session["updated_at"] = datetime.utcnow().isoformat()
                STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=_ui_for_phase(2),
                    progress=_progress(2),
                    state=session,
                )
            if "disponibilité" in choice:
                session["phase"] = 3
                session["step_id"] = "phase_3"
                _maybe_append_indicative_calc(session, messages)
                message = _render_assistant_message(
                    "phase_3",
                    session,
                    _phase3_prompt(session),
                    ["Accès à tout moment", "Occasionnellement", "Uniquement à l’échéance", "Pas besoin d’y toucher"],
                )
                messages.append(Message(role="assistant", content=message))
                session["updated_at"] = datetime.utcnow().isoformat()
                STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=_ui_for_phase(3),
                    progress=_progress(3),
                    state=session,
                )
            if "confort" in choice or "variations" in choice:
                policy, policy_source = _risk_policy(session)
                session["debug_entered_phase"] = 4
                session["debug_risk_policy_used"] = policy
                session["debug_risk_policy_source"] = policy_source
                if policy == "skip":
                    session["debug_generated_risk_question"] = False
                    return _advance_to_phase5_after_risk_skip(request.session_id, session, messages)
                session["phase"] = 4
                session["step_id"] = "phase_4"
                session["debug_generated_risk_question"] = True
                message = _render_assistant_message(
                    "phase_4",
                    session,
                    PHASE_PROMPTS[4],
                    _risk_options(policy),
                )
                messages.append(Message(role="assistant", content=message))
                session["updated_at"] = datetime.utcnow().isoformat()
                STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=UIState(type="quick_replies", quick_replies=_risk_options(policy)),
                    progress=_progress(4),
                    state=session,
                )
            if "offres" in choice:
                if _is_short_term_horizon(session):
                    if "answers" in session:
                        session["answers"]["exclusives_opt_in"] = _answer_value(
                            False,
                            1.0,
                            "system_rule",
                        )
                    messages.append(Message(
                        role="assistant",
                        content="Pour un objectif à moins d’un an, on privilégie des solutions simples et liquides plutôt que des projets immobilisés."
                    ))
                    session["step_id"] = "phase_7"
                    session["phase"] = 7
                    if not session.get("phase7_recap"):
                        tone_style = session.get("tone_style") or detect_tone_style(session)
                        session["tone_style"] = tone_style
                        recap = compose_final_advisor_recap(session.get("answers", {}), tone_style)
                        session["phase7_recap"] = recap.model_dump()
                    messages.append(Message(role="assistant", content=_format_phase7_recap(session["phase7_recap"])))
                    session["step_id"] = "phase_7_next"
                    session["updated_at"] = datetime.utcnow().isoformat()
                    STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                    return StepResponse(
                        session_id=request.session_id,
                        messages=messages,
                        ui=UIState(
                            type="quick_replies",
                            quick_replies=(session.get("phase7_recap") or {}).get(
                                "next_steps",
                                ["Activer cette stratégie", "Revoir un point"],
                            ),
                        ),
                        progress=_progress(7),
                        state=session,
                    )
                session["phase"] = 6
                session["step_id"] = "exclusive_allocations"
                messages.append(Message(role="assistant", content=f"{PHASE_PROMPTS[6]}\n\n{_build_offers_text_for_state(session)}"))
                session["updated_at"] = datetime.utcnow().isoformat()
                STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)
                return StepResponse(
                    session_id=request.session_id,
                    messages=messages,
                    ui=_allocation_ui_for_state(session),
                    progress=_progress(6),
                    state=session,
                )

        if not session.get("phase7_recap"):
            tone_style = session.get("tone_style") or detect_tone_style(session)
            session["tone_style"] = tone_style
            recap = compose_final_advisor_recap(session.get("answers", {}), tone_style)
            session["phase7_recap"] = recap.model_dump()
        messages.append(Message(role="assistant", content=_format_phase7_recap(session["phase7_recap"])))

    session["phase"] = phase
    session["updated_at"] = datetime.utcnow().isoformat()
    STORE.update(request.session_id, session, DEFAULT_TTL_SECONDS)

    return StepResponse(
        session_id=request.session_id,
        messages=messages,
        ui=_ui_for_phase(phase),
        progress=_progress(phase),
        state=session,
    )


def get_state(session_id: str) -> StateResponse:
    session = STORE.get(session_id)
    if not session:
        raise ValueError("Session not found or expired")

    return StateResponse(
        session_id=session_id,
        phase=session.get("phase", 1),
        state=session,
    )
