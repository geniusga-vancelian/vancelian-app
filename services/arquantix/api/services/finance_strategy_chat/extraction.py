"""
OpenAI JSON strict extraction: extract_patch(profile, last_question, user_text) -> PatchResult
"""
import json
import os
import re
from typing import Optional, Dict, Any
import httpx

from .schemas import ClientProfile, PatchResult, PatchUpdate, PatchNormalized, LastQuestion

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

SYSTEM_PROMPT = """
Tu es Vancelian Coach.
Ta mission: extraire un PATCH JSON STRICT à partir de la réponse utilisateur.

Règles:
- Par défaut, range la réponse dans expected_fields[0] si présent.
- Si le texte indique clairement un autre champ (ex: \"par mois\"), reroute vers le bon champ.
- Ne mets jamais du texte dans un champ money: valeurs numériques ou null.
- Si rien d’exploitable, updates=[].
- Si expected_fields contient goal.type, renvoie une valeur CANONIQUE: travel|purchase|real_estate|retirement|safety|unknown.
- Fixe la confidence selon la clarté (0.5 vague, 0.85 clair, 0.95 explicite).

Chemins cibles (priorité):
- goal.type
- goal.target_amount
- timeline.horizon_months
- capacity.monthly_contribution
- risk.tolerance_score
- knowledge_level

Règles last_question.text -> champ préféré:
- "montant total", "objectif", "budget total", "cible" => target_amount
- "au départ", "somme de départ" => initial_contribution_amount
- "par mois", "mensuel" => monthly_contribution_amount

Sortie JSON STRICT:
{
  "updates": [{"path":"goal.target_amount","value":4500,"confidence":0.92,"source":"user_text"}],
  "notes": ["..."],
  "normalized": {"money":{"amount":4500,"period":"monthly|one_time|total|unknown","currency":"EUR"}}
}
"""


_AMOUNT_RE = re.compile(r"(\d{1,3}(?:[\s.,]\d{3})*|\d+)(?:[\s]?)(€|eur|euros)?", re.IGNORECASE)


def _parse_amount(text: str) -> Optional[float]:
    if not text:
        return None
    match = _AMOUNT_RE.search(text.replace("\u202f", " "))
    if not match:
        return None
    raw = match.group(1)
    raw = raw.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _preferred_key_from_question(question_text: str) -> Optional[str]:
    if not question_text:
        return None
    lower = question_text.lower()
    if any(token in lower for token in ["montant total", "objectif", "budget total", "cible"]):
        return "target_amount"
    if any(token in lower for token in ["au départ", "somme de départ"]):
        return "initial_contribution_amount"
    if any(token in lower for token in ["par mois", "mensuel"]):
        return "monthly_contribution_amount"
    return None


def _route_key(expected_key: Optional[str], question_text: str, user_text: str) -> tuple[str, str]:
    text = (user_text or "").lower()
    if any(token in text for token in ["par mois", "mensuel", "/mois"]):
        if expected_key != "capacity.monthly_contribution":
            return "capacity.monthly_contribution", "rerouted"
    if any(token in text for token in ["au départ", "somme de départ", "initial"]):
        if expected_key != "goal.initial_contribution_amount":
            return "goal.initial_contribution_amount", "rerouted"
    if any(token in text for token in ["objectif", "cible", "budget total", "montant total"]):
        if expected_key != "goal.target_amount":
            return "goal.target_amount", "rerouted"
    preferred = _preferred_key_from_question(question_text)
    if preferred:
        if preferred == "target_amount":
            return "goal.target_amount", "question_preference"
        if preferred == "initial_contribution_amount":
            return "goal.initial_contribution_amount", "question_preference"
        if preferred == "monthly_contribution_amount":
            return "capacity.monthly_contribution", "question_preference"
    return expected_key or "", "default_expected"


def _infer_project_type(user_text: str) -> Optional[str]:
    lower = (user_text or "").lower()
    if any(token in lower for token in ["voyage", "vacances", "nyc", "maldives", "japon", "trip"]):
        return "travel"
    if any(token in lower for token in ["achat", "voiture", "sac", "objet", "plaisir", "bien matériel"]):
        return "purchase"
    if any(token in lower for token in ["immobilier", "apport", "maison", "appart", "logement", "locatif"]):
        return "real_estate"
    if any(token in lower for token in ["retraite", "avenir", "long terme"]):
        return "retirement"
    if any(token in lower for token in ["sécurité", "filet", "matelas", "urgence", "serein", "serenit"]):
        return "safety"
    return None


def _heuristic_patch(profile: ClientProfile, user_text: str, last_question: Optional[LastQuestion]) -> PatchResult:
    expected_key = (last_question.expected_fields[0] if last_question and last_question.expected_fields else None)
    question_text = last_question.text if last_question else ""
    routed_to, reason = _route_key(expected_key, question_text, user_text)

    updates = []
    notes = []
    amount = _parse_amount(user_text)
    lower = (user_text or "").lower()
    if any(token in lower for token in ["cadre simple", "simple", "aller à l'essentiel", "aller a l'essentiel"]):
        updates.append(
            PatchUpdate(
                path="preferences.mode",
                value="simple",
                confidence=0.8,
                source="user_choice",
            )
        )

    if routed_to in {"goal.target_amount", "goal.initial_contribution_amount", "capacity.monthly_contribution"}:
        if amount is not None:
            updates.append(
                PatchUpdate(
                    path=routed_to,
                    value=amount,
                    confidence=0.9,
                    source="user_text",
                )
            )
            if expected_key and routed_to != expected_key:
                notes.append("rerouted amount to correct field")
    elif routed_to == "goal.type":
        inferred = _infer_project_type(user_text)
        updates.append(
            PatchUpdate(
                path="goal.type",
                value=inferred or user_text,
                confidence=0.85 if inferred else 0.6,
                source="user_text",
            )
        )
    elif routed_to == "goal.description":
        updates.append(
            PatchUpdate(
                path="profile.project_summary",
                value=user_text,
                confidence=0.7,
                source="user_text",
            )
        )
    elif routed_to == "capacity.initial_amount":
        if amount is not None:
            updates.append(
                PatchUpdate(
                    path="goal.initial_contribution_amount",
                    value=amount,
                    confidence=0.9,
                    source="user_text",
                )
            )
    elif routed_to in {"timeline.horizon_months", "liquidity", "intent", "project_summary"}:
        updates.append(
            PatchUpdate(
                path=routed_to if "." in routed_to else f"profile.{routed_to}",
                value=user_text,
                confidence=0.7,
                source="user_text",
            )
        )

    normalized = None
    if amount is not None:
        normalized = PatchNormalized(
            money={"amount": amount, "period": "unknown", "currency": "EUR"}
        )

    return PatchResult(updates=updates, notes=notes, normalized=normalized)


def extract_patch(profile: ClientProfile, last_question: Optional[LastQuestion], user_text: str) -> PatchResult:
    if not OPENAI_API_KEY:
        return _heuristic_patch(profile, user_text, last_question)

    question_text = last_question.text if last_question else ""
    question_id = last_question.id if last_question else ""
    expected_fields = last_question.expected_fields if last_question else []
    user_prompt = (
        f"last_question.id: {question_id}\n"
        f"last_question.text: {question_text}\n"
        f"last_question.expected_fields: {expected_fields}\n"
        f"user_text: {user_text}\n"
        f"profile: {profile.model_dump()}\n"
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

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
        return PatchResult(**parsed)
    except Exception:
        return _heuristic_patch(profile, user_text, last_question)
