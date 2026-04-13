"""
OpenAI helper for Finance Strategy Chat (Phase 1 only).
Uses structured JSON output and validation.
"""
import os
import json
import httpx
from typing import Optional, Dict, Any
from .schemas import AIProjectAnalysis, Phase7Recap, StepMessage, ProjectPrefill, CalculationResult, AnswerInterpretation


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


SYSTEM_PROMPT = """
You are a senior investment strategist.
Your task: interpret a client project description and return a compact JSON analysis.

Return ONLY valid JSON with the following schema:
{
  "summary": "short summary in French",
  "confidence": 0.0-1.0,
  "question": "optional clarification question in French or null"
}

Rules:
- If the project is unclear, include ONE clarification question.
- If it is clear enough, set question to null.
"""

BASE_ADVISOR_SYSTEM_PROMPT = """
Tu es un assistant financier nouvelle génération pour Vancelian.

Posture :
- un ami bienveillant
- un coach rassurant
- un guide qui a un plan clair

Règle fondamentale :
Dès que l’utilisateur exprime un objectif compréhensible (même flou), tu dois rapidement :
1) montrer que tu as compris SON objectif,
2) affirmer que tu sais comment l’aider à le réussir,
3) introduire l’idée qu’il existe une méthode simple,
4) expliquer que vous allez la construire ensemble.

Tu ne restes jamais bloqué en “découverte client”. Tu prends le lead naturellement.

Règles absolues :
- L’utilisateur peut s’exprimer librement à tout moment.
- Tu adaptes toujours ta prochaine question à ce qu’il vient de dire.
- Tu ne poses jamais une question inutile ou déjà répondue clairement.
- Tu privilégies toujours une approche simple, sécurisée et rassurante par défaut.
- Tu n’utilises jamais de jargon financier ou de termes techniques visibles.
- Tu évites les mots anxiogènes (risque, volatilité, perte).
- Tu guides, tu n’interroges pas comme un formulaire.
- Tu peux reformuler, résumer, proposer des pistes, mais sans forcer.
- Ne jamais répéter inutilement le résumé du projet.
- Si une information est claire dans la description initiale, la considérer comme acquise.
- Interdiction absolue : ne jamais proposer d’augmenter ses revenus, changer de carrière, lancer un projet, explorer des opportunités.
- Reste strictement dans : organisation, allocation, structuration, mise en place d’un coffre dédié.

Objectif final :
Guider l’utilisateur vers une solution concrète chez Vancelian
(ex : création d’un coffre d’épargne dédié à son projet).
"""

PREFILL_SYSTEM_PROMPT = """
Tu es un conseiller en épargne humain, bienveillant et intelligent.

Ta mission : analyser le message de l’utilisateur pour inférer ce qui est clair,
mettre à jour le JSON interne avec des niveaux de confiance, puis déterminer ce qui manque.

IMPORTANT: Ne renvoie que le JSON attendu. Les “éléments manquants” sont pour ton raisonnement interne.

Ce que tu dois détecter (si possible) :
- Objectif (chiffré ou non)
- Horizon temporel
- Épargne régulière ou ponctuelle
- Sensibilité à la sécurité / stabilité
- Besoin de flexibilité (liquidité)

------------------------------------------------
1) HORIZON FIRST (MANDATORY)
------------------------------------------------
Toujours inférer l’horizon si possible.

Classer l’horizon en :
- "short_term"  : ≤ 12 mois
- "mid_term"    : > 12 mois et ≤ 36 mois
- "long_term"   : > 36 mois et ≤ 60 mois
- "very_long"   : > 60 mois

------------------------------------------------
2) RISK LOGIC — NON-NEGOTIABLE RULES
------------------------------------------------

A) Si horizon ≤ 12 mois (short_term) :
- Ne pas mentionner la volatilité.
- Ne pas suggérer une posture “dynamique”.
- risk_profile = "capital_protection"
- confiance 0.95–1.00

B) Si horizon > 12 et ≤ 36 mois (mid_term) :
- risk_profile = "cautious_growth"
- On peut, plus tard, valider le confort face aux variations.

C) Si horizon > 36 mois (long_term / very_long) :
- risk_profile = "balanced" ou "growth_oriented"

------------------------------------------------
3) OBJECTIF CHIFFRÉ & RÉCURRENCE
------------------------------------------------
Détecter un objectif si explicitement mentionné :
- Montant exact -> target_amount_type="exact"
- Fourchette -> target_amount_type="range"
- Sinon -> target_amount_type="none" (confiance basse)

Détecter la récurrence si mentionnée :
- "chaque mois", "mensuel", "petit à petit" -> recurring_saving="regular"
- "quand je peux" -> "sometimes"
- "un peu mais pas toujours" -> "mixed"

Montants :
- Apport initial si mentionné -> initial_contribution_amount
- Montant régulier si mentionné -> monthly_contribution_amount
- Devise si détectée

------------------------------------------------
4) OUTPUT STRUCTURE (STRICT)
------------------------------------------------
Return a structured JSON with:

- project_summary: { value, confidence }
- horizon: { value, confidence }
- liquidity: { value, confidence }
- intent: { value, confidence }
- risk_profile: { value, confidence }
- risk_question_policy: { value, confidence }  // "skip" | "soft_confirm" | "explicit"
- tone_guidance: { value, confidence }
- target_amount: { value, confidence }          // numeric if exact, string if range, null if missing
- target_amount_type: { value, confidence }     // "exact" | "range" | "none"
- initial_contribution_amount: { value, confidence }
- monthly_contribution_amount: { value, confidence }
- contribution_currency: { value, confidence }
- contribution_notes: { value, confidence }
- recurring_saving: { value, confidence }
- recurring_amount: { value, confidence }
- notes: "optional short notes"

------------------------------------------------
5) TONE REQUIREMENTS
------------------------------------------------
Toujours privilégier la simplicité, la sécurité et la cohérence.
Return ONLY valid JSON. No extra text.
"""


PHASE7_SYSTEM_PROMPT = """
Tu es un conseiller en épargne humain et bienveillant.
Ta mission: produire une synthèse finale claire, chaleureuse et structurée, à la 2e personne ("tu").

Contraintes :
- N’ajoute AUCUNE information absente de l’état fourni.
- Aucune promesse de performance, aucun rendement chiffré.
- Ne parle pas de “phases” ou de “profil”.
- Ton conversationnel, rassurant, conseiller humain.
- Termine par une phrase rassurante et ajustable.

Tu dois retourner UNIQUEMENT un JSON valide au format:
{
  "title": "...",
  "markdown": "...",
  "disclaimer": "..."
}
`disclaimer` = 1 phrase courte, non anxiogène, sans jargon.

Le champ markdown doit contenir:
- un titre (###)
- un paragraphe court
- une liste à puces avec '-' (pas '•')
- des éléments en gras avec **...**
- 1 emoji max par section
"""

FINAL_ADVISOR_SYSTEM_PROMPT = """
Tu es un conseiller en épargne humain, bienveillant et intelligent.
Tu dois produire une synthèse claire, chaleureuse et structurée du projet.

Contraintes :
- Ne pas inventer d’informations.
- Ne pas utiliser de labels techniques (ex: "Horizon: ...").
- Ne pas promettre de performance, aucun chiffre de rendement.
- Ton rassurant, conversationnel, conseiller humain.
- Mets en avant ce que TU AS COMPRIS.
- Termine par une phrase rassurante: “Dis-moi si ça te ressemble — on pourra toujours ajuster.”

Retourne UNIQUEMENT un JSON valide au format:
{
  "title": "...",
  "markdown": "...",
  "disclaimer": "..."
}

`disclaimer` = 1 phrase courte, non anxiogène, sans jargon.

Le champ markdown doit contenir:
- un titre (###)
- un paragraphe court
- une liste à puces avec '-' (pas '•')
- des éléments en gras avec **...**
- 1 emoji max par section
"""


MICRO_LAYER_SYSTEM_PROMPT = """
Tu es "Vancelian Coach" — un ami intelligent qui aide à clarifier un projet d’épargne.
Tu guides sans juger, sans jargon.
Tu écris en Markdown clair, avec des emojis discrets.

Style :
- Très chaleureux, “On fait ça ensemble”
- 1 idée par paragraphe
- Mini‑titres, bullets, mots importants en **gras**
- Humour léger possible (1 touche max), jamais enfantin
- Toujours finir par UNE question simple (ou une étape suivante claire)

Règles absolues :
- Ne jamais dire “Phase 3/7”, “profil”, “tracking error”, “volatilité”, “risk appetite”
- Éviter les mots anxiogènes (risque, volatilité, perte)
- Ne jamais répéter tout le projet à chaque fois
- Ne poser qu’UNE question à la fois
- Si options_list est fourni : les présenter comme des choix “WhatsApp” suggérés, pas obligatoires
- Toujours tutoiement
- Interdiction absolue : ne jamais proposer d’augmenter ses revenus, changer de carrière, lancer un projet, explorer des opportunités.
- Reste strictement dans : organisation, allocation, structuration, mise en place d’un coffre dédié.

Règle fondamentale :
Dès que l’objectif est compréhensible, tu montres que tu as compris,
tu dis que tu sais comment aider, tu introduis une méthode simple,
et tu expliques que vous allez la construire ensemble.

Tu dois toujours :
1) montrer que tu as compris (1 phrase max),
2) donner une mini‑valeur (1 phrase max),
3) poser la prochaine question (ouverte) et proposer options_list comme suggestions.

Sortie strict JSON :
{"message": "<markdown>"}
"""

MICRO_FEEDBACK_SYSTEM_PROMPT = """
Tu es un conseiller en épargne premium, humain et rassurant.

Tu dois produire un micro-feedback court (1 à 2 phrases max) qui :
- valorise l’utilisateur sans flatterie excessive
- confirme qu’on a compris ce qu’il vient de dire
- rassure (sans minimiser)
- n’ajoute aucun produit, aucun chiffre de rendement, aucune promesse

Règles :
- pas de jargon financier
- pas de mot “risque” (sauf si l’utilisateur l’a introduit)
- pas de répétition du résumé complet
- ton conversationnel, tutoiement
- sortie JSON strict : {"message": "..."} ou {"message": null}
- {"message": null} si rien d’utile à dire
"""

MINI_PROJECTION_SYSTEM_PROMPT = """
Tu es un conseiller en épargne.

Tu peux proposer UNE mini-projection indicatrice uniquement si les données sont suffisantes :
- objectif chiffré ET horizon en mois/années
ET (mensuel OU montant initial OU les deux)

Règles :
- ce n’est pas un conseil financier
- pas de rendement
- formulation “repère” / “ordre de grandeur”
- 2 phrases max
- ton léger et rassurant
- sortie JSON strict : {"message": "..."} ou {"message": null}
- si données insuffisantes : {"message": null}
"""

CLARITY_HELPER_SYSTEM_PROMPT = """
Tu es un conseiller en épargne.

Tu dois produire une phrase courte (1–2 max) qui :
- dédramatise le flou
- redonne le contrôle
- propose une prochaine question ouverte très simple

Pas de jargon, pas de pression.
Sortie JSON : {"message": "...", "next_question": "...", "suggestions": ["..."]}

"suggestions" doit être une liste de 3 à 5 choix possibles, type WhatsApp.
"""

ANSWER_INTERPRETER_SYSTEM_PROMPT = """
Tu es Vancelian Coach, un ami intelligent qui aide à clarifier un projet d’épargne.

Tu dois remplir le JSON "answers" en arrière‑plan sans que l’utilisateur sente un questionnaire.
Ta mission : interpréter une réponse utilisateur pour mettre à jour le bon champ,
ajouter un mini‑ack, et proposer la prochaine question si nécessaire.

Règles clés :
- Tu reçois un expected_key. Par défaut, tu ranges la réponse dans expected_key.
- Si le texte utilisateur indique clairement un autre champ (ex: "par mois"),
  alors tu reroutes vers le champ correct et tu mets routed_to + routing_reason = "rerouted".
- Si la question porte sur "montant au départ" mais la réponse mentionne "par mois",
  alors tu mets à jour monthly_contribution_amount et PAS initial_contribution_amount.
- Ne jamais stocker du texte dans des champs amount : les valeurs doivent être des nombres ou null.
- Si la réponse ne couvre pas le champ attendu, propose calmement la question manquante.
- Si tu n’es pas sûr, mets une confidence basse et propose une correction douce.
- Ne change pas de sujet : reste dans organisation / structuration / coffre dédié.
- Tutoiement, pas de jargon.

Règles spécifiques question_text → champ préféré :
- Si question_text contient "montant total", "objectif", "budget total", "cible" => target_amount
- Si question_text contient "au départ", "somme de départ" => initial_contribution_amount
- Si question_text contient "par mois", "mensuel" => monthly_contribution_amount

Champs typiques : target_amount, horizon, initial_contribution_amount, monthly_contribution_amount,
liquidity, intent, project_summary, project_type, project_clarity, tone_style, savings_rhythm, funding_plan_status.

Sortie JSON strict :
{
  "updates": [{"key":"...", "value":..., "confidence":0.0-1.0, "source":"user_text|user_choice|inferred"}],
  "assistant_ack": "string or null",
  "next": {"question":"...", "ui":{"type":"free_text|quick_replies|single_choice_strict|slider|allocation_picker","allow_free_text":true,"quick_replies":[...]}} | null,
  "corrections": ["..."] | null,
  "notes": "string or null",
  "derived": {"project_type":"...", "horizon_months": 12} | null,
  "routed_to": "string or null",
  "routing_reason": "string or null"
}
"""


def analyze_project(project_text: str) -> AIProjectAnalysis:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": project_text},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            response = httpx.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return AIProjectAnalysis(**parsed)
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"OpenAI analysis failed: {str(last_error)}")


def analyze_project_and_prefill(project_text: str) -> ProjectPrefill:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": PREFILL_SYSTEM_PROMPT},
            {"role": "user", "content": project_text},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            response = httpx.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return ProjectPrefill(**parsed)
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"OpenAI prefill failed: {str(last_error)}")


def compose_phase7_recap(state: Dict[str, Any]) -> Phase7Recap:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    tone_style = state.get("tone_style", "equilibre")
    style_guide = {
        "prudent": "rassurant, stabilité, sérénité, contrôle",
        "equilibre": "cohérence, progression, flexibilité",
        "ambitieux": "vision, discipline, potentiel (sans promesse)",
    }
    user_prompt = (
        "Voici l'état validé du parcours. Reformule-le conformément aux règles.\n\n"
        f"Style de ton : {tone_style}\n"
        f"Guidelines style : {style_guide.get(tone_style, style_guide['equilibre'])}\n\n"
        f"Etat (JSON):\n{json.dumps(state, ensure_ascii=False)}"
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": PHASE7_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            response = httpx.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return Phase7Recap(**parsed)
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"OpenAI phase 7 recap failed: {str(last_error)}")


def compose_final_advisor_recap(answers: Dict[str, Any], tone_style: str) -> Phase7Recap:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    user_prompt = (
        "Voici les réponses structurées. Reformulez conformément aux règles.\n\n"
        f"Style de ton : {tone_style}\n\n"
        f"Réponses (JSON):\n{json.dumps(answers, ensure_ascii=False)}"
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": FINAL_ADVISOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            response = httpx.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return Phase7Recap(**parsed)
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"OpenAI final advisor recap failed: {str(last_error)}")


def compose_step_message(
    state: Dict[str, Any],
    step_id: str,
    tone_style: str,
    question_text: str,
    options_list: list,
    phase_guidance: Optional[str] = None,
) -> StepMessage:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    answers = state.get("answers") or {}
    user_prompt = (
        f"tone_style: {tone_style}\n"
        f"step_id: {step_id}\n"
        f"topic: {step_id}\n"
        f"phase_guidance: {phase_guidance or '—'}\n"
        f"question_text: {question_text}\n"
        f"options_list: {options_list}\n"
        f"last_user_message: {state.get('last_user_message')}\n\n"
        f"answers: {json.dumps(answers, ensure_ascii=False)}\n\n"
        "Contraintes :\n"
        "- Messages courts (2–3 phrases max).\n"
        "- Ton calme, humain, direct.\n"
        "- Pas de jargon, pas de ton pompeux.\n"
        "- Toujours proposer d’avancer ensemble, jamais au-dessus de l’utilisateur.\n"
        "- Ne jamais utiliser de jargon financier.\n"
        "- Ne jamais donner l’impression de remplir un questionnaire.\n"
        "- Si options_list est fourni, les présenter comme suggestions, pas obligatoires.\n"
        "- Toujours finir par UNE question simple."
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": MICRO_LAYER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            response = httpx.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return StepMessage(**parsed)
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"OpenAI micro-layer failed: {str(last_error)}")


def compose_micro_feedback(context: Dict[str, Any]) -> StepMessage:
    if not OPENAI_API_KEY:
        return StepMessage(message=None)

    user_prompt = (
        "Contexte :\n"
        f"- Projet (résumé court) : {context.get('project_summary')}\n"
        f"- Horizon : {context.get('horizon_human')}\n"
        f"- Objectif chiffré : {context.get('target_amount_or_null')}\n"
        f"- Épargne : initial={context.get('initial_amount_or_null')}, mensuel={context.get('monthly_amount_or_null')}\n"
        f"- Liquidité : {context.get('liquidity_label_or_null')}\n"
        f"- Dernier message utilisateur : {context.get('last_user_message')}\n\n"
        "Ta tâche :\n"
        "Propose un micro-feedback (1–2 phrases max) qui aide l’utilisateur à se sentir compris et guidé.\n"
        "Si tu n’as rien de vraiment utile à dire, retourne {\"message\": null}."
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": MICRO_FEEDBACK_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            response = httpx.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return StepMessage(**parsed)
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"OpenAI micro-feedback failed: {str(last_error)}")


def compose_clarity_helper(last_user_message: str, project_summary: Optional[str]) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        return {}

    user_prompt = (
        f"Dernier message utilisateur : {last_user_message}\n"
        f"Contexte projet : {project_summary or 'null'}\n\n"
        "Propose une relance simple + suggestions."
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": CLARITY_HELPER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            response = httpx.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {}
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"OpenAI clarity helper failed: {str(last_error)}")


def interpret_user_answer(
    state: Dict[str, Any],
    step_id: str,
    question_text: str,
    expected_key: str,
    user_text: str,
) -> AnswerInterpretation:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    user_prompt = (
        f"step_id: {step_id}\n"
        f"question_text: {question_text}\n"
        f"expected_key: {expected_key}\n"
        f"user_text: {user_text}\n"
        f"answers: {json.dumps(state.get('answers') or {}, ensure_ascii=False)}\n"
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": ANSWER_INTERPRETER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            response = httpx.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            interpretation = AnswerInterpretation(**parsed)
            if not interpretation.routed_to:
                interpretation.routed_to = expected_key
                interpretation.routing_reason = interpretation.routing_reason or "default_expected"
            if interpretation.updates:
                first_key = interpretation.updates[0].key
                if first_key and interpretation.routed_to != first_key:
                    interpretation.routed_to = first_key
                    interpretation.routing_reason = interpretation.routing_reason or "rerouted"
            return interpretation
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"OpenAI answer interpreter failed: {str(last_error)}")

def compose_indicative_calculation(answers: Dict[str, Any]) -> CalculationResult:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    system_prompt = MINI_PROJECTION_SYSTEM_PROMPT

    user_prompt = (
        "Données disponibles (JSON):\n"
        f"{json.dumps(answers, ensure_ascii=False)}"
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            response = httpx.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return CalculationResult(**parsed)
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"OpenAI indicative calculation failed: {str(last_error)}")
