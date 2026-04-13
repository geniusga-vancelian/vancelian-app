"""
Agent Extractor: structured extraction from user message with confidence and source_quote.
Fallback heuristics when OPENAI_API_KEY is missing.
"""
from __future__ import annotations

import json
import re
from typing import Any

from ._llm import chat, load_prompt

_AMOUNT_RE = re.compile(r"(\d{1,3}(?:[\s.,]\d{3})*|\d+)\s*(?:€|eur|euros)?", re.IGNORECASE)
_YEARS_RE = re.compile(r"(\d+)\s*ans?", re.IGNORECASE)
_MONTHS_RE = re.compile(r"(\d+)\s*mois", re.IGNORECASE)
_MONTHLY_RE = re.compile(r"(\d{1,3}(?:[\s.,]\d{3})*|\d+)\s*(?:€|eur|euros?)?\s*(?:\/|par)\s*mois", re.IGNORECASE)
_WEEKLY_RE = re.compile(r"(\d{1,3}(?:[\s.,]\d{3})*|\d+)\s*(?:€|eur|euros?)?\s*(?:\/|par)\s*semaine", re.IGNORECASE)
# Risque Q_RISK_CALIB : A→6–7, B→2–3, C→4–5
_RISK_A_RE = re.compile(r"(?:^|[\s,])[Aa]\s*\)?(\s|$|,|\.)", re.IGNORECASE)
_RISK_B_RE = re.compile(r"(?:^|[\s,])[Bb]\s*\)?(\s|$|,|\.)", re.IGNORECASE)
_RISK_C_RE = re.compile(r"(?:^|[\s,])[Cc]\s*\)?(\s|$|,|\.)", re.IGNORECASE)
# Réponses très courtes A/B/C
_RISK_ONLY_A = re.compile(r"^[Aa]\s*\)?$")
_RISK_ONLY_B = re.compile(r"^[Bb]\s*\)?$")
_RISK_ONLY_C = re.compile(r"^[Cc]\s*\)?$")
_FREQ_MONTHLY_RE = re.compile(r"(par|chaque)\s+mois|mensuel|mensuellement|tous les mois", re.IGNORECASE)
_FREQ_WEEKLY_RE = re.compile(r"(par|chaque)\s+semaine|hebdo|hebdomadaire", re.IGNORECASE)
_INITIAL_HINT_RE = re.compile(r"(au\s+d[ée]part|au\s+début|d[ée]part)", re.IGNORECASE)
_VAGUE_AMOUNT_RE = re.compile(r"\b(un peu|quelque chose|un petit coup de pouce)\b", re.IGNORECASE)
_REGULAR_HINT_RE = re.compile(r"(r[ée]guli|chaque|mensuel|mensuellement|hebdo|hebdomadaire)", re.IGNORECASE)
_NO_INITIAL_RE = re.compile(r"(rien|aucun|pas de|0)\s*(?:€|eur|euros)?\s*(?:au\s+d[ée]part|au\s+début)", re.IGNORECASE)
_NO_MONTHLY_RE = re.compile(r"(rien|aucun|pas de|0)\s*(?:€|eur|euros)?\s*(?:par|\/)\s*(mois|semaine)", re.IGNORECASE)
_LIQUIDITY_WITHDRAW_RE = re.compile(r"(retir|r[ée]cup|recup|pioch|sortir|toucher)", re.IGNORECASE)
_LIQUIDITY_NEGATIVE_RE = re.compile(
    r"(pas\s+(?:y\s+)?toucher|ne\s+pas\s+(?:y\s+)?toucher|laisser\s+(?:cette\s+)?[ée]pargne\s+intacte|sans\s+retrait|aucun\s+retrait|pas\s+de\s+retrait)",
    re.IGNORECASE,
)
_LIQUIDITY_FLEX_RE = re.compile(r"(souplesse|flexib|au\s+cas\s+o[uù]|si\s+besoin|en\s+cas\s+d['’]impr[ée]vu|impr[ée]vu)", re.IGNORECASE)
_LIQUIDITY_HIGH_RE = re.compile(r"(souvent|r[ée]guli[èe]rement|fr[ée]quemment|besoin\s+souvent|j['’]aurai\s+besoin|important|indispensable)", re.IGNORECASE)

_PROJECT_TYPE_KEYWORDS = {
    "buy_something": {
        "strong": ["achat", "acheter", "appartement", "maison", "voiture", "sac", "montre", "travaux"],
        "weak": ["acheter quelque chose", "me faire plaisir"],
    },
    "live_better": {
        "strong": ["finir le mois", "plus à l’aise", "plus a l'aise", "confort", "pression"],
        "weak": ["mieux vivre", "quotidien", "revenus"],
    },
    "prepare_future": {
        "strong": ["retraite", "avenir", "long terme", "tranquillité"],
        "weak": ["sécurité", "indépendant", "independante"],
    },
    "protect_family": {
        "strong": ["enfants", "études", "etudes", "famille", "proches", "héritage", "heritage"],
        "weak": ["transmission", "protéger"],
    },
    "experiences": {
        "strong": ["voyage", "tour du monde", "expérience", "experience", "sabbatique"],
        "weak": ["loisirs", "projet perso"],
    },
    "grow_money": {
        "strong": ["investir", "rendement", "fructifier", "inflation", "diversification"],
        "weak": ["faire travailler", "opportunité", "opportunite"],
    },
}

_PROJECT_TYPE_LABELS = {
    "acheter quelque chose": "buy_something",
    "mieux vivre au quotidien": "live_better",
    "preparer mon avenir": "prepare_future",
    "préparer mon avenir": "prepare_future",
    "proteger mes proches": "protect_family",
    "protéger mes proches": "protect_family",
    "vivre des expériences": "experiences",
    "vivre des experiences": "experiences",
    "faire fructifier mon argent": "grow_money",
}

_VOWELS = set("aeiouyàâäéèêëîïôöùûüÿ")
_COMMON_WORDS = {
    "je",
    "tu",
    "il",
    "elle",
    "nous",
    "vous",
    "ils",
    "elles",
    "mon",
    "ma",
    "mes",
    "pour",
    "avec",
    "dans",
    "sur",
    "a",
    "à",
    "de",
    "le",
    "la",
    "les",
    "un",
    "une",
    "des",
    "et",
    "ou",
}


def _collect_user_text(last_turns: list[dict[str, str]]) -> str:
    text = ""
    for t in last_turns:
        if t.get("role") == "user":
            text = (text + " " + (t.get("content") or "")).strip()
    return text


def _last_user_message(last_turns: list[dict[str, str]]) -> str:
    for t in reversed(last_turns):
        if t.get("role") == "user":
            return (t.get("content") or "").strip()
    return ""


def _normalize_label(raw: str) -> str:
    no_emoji = re.sub(r"[\U00010000-\U0010ffff]", "", raw)
    cleaned = re.sub(r"[^\w\sàâäéèêëîïôöùûüÿ'-]", "", no_emoji, flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned.strip().lower())


def _label_override(text: str) -> list[dict[str, Any]] | None:
    label_key = _normalize_label(text)
    if label_key in _PROJECT_TYPE_LABELS:
        project_type = _PROJECT_TYPE_LABELS[label_key]
        return [
            {"field": "project_type", "value": project_type, "confidence": 0.95, "source_quote": text},
            {"field": "project_type_confidence", "value": 0.95, "confidence": 0.95, "source_quote": text},
            {"field": "project_type_source", "value": "chip", "confidence": 0.9, "source_quote": text},
            {"field": "goal_confidence", "value": 0.95, "confidence": 0.95, "source_quote": text},
            {"field": "goal_locked", "value": True, "confidence": 0.95, "source_quote": text},
        ]
    return None


def run_extractor(
    last_turns: list[dict[str, str]],
    profile_partial: dict,
    asked_questions: list[str],
    llm: object | None = None,
) -> dict[str, Any]:
    """
    Returns: { "extracted": [{"field", "value", "confidence", "source_quote"}], "missing_fields": [], "contradictions": [] }
    """
    last_user = _last_user_message(last_turns)
    if last_user:
        label_fields = _label_override(last_user)
        if label_fields:
            return {"extracted": label_fields, "missing_fields": [], "contradictions": []}
    system = load_prompt("extractor")
    user = (
        f"last_turns: {json.dumps(last_turns, ensure_ascii=False)}\n"
        f"profile_partial: {json.dumps(profile_partial, ensure_ascii=False)}\n"
        f"asked_questions: {asked_questions}\n\n"
        "Réponds en JSON strict avec extracted, missing_fields, contradictions."
    )
    if llm is not None and hasattr(llm, "chat"):
        out = llm.chat(system, user, json_mode=True, temperature=0.1)
    elif not system or not _has_openai():
        return _heuristic_extract(last_turns, profile_partial, asked_questions)
    else:
        out = chat(system, user, json_mode=True, temperature=0.1)
    if not out:
        return _heuristic_extract(last_turns, profile_partial, asked_questions)
    try:
        data = json.loads(out)
        return {
            "extracted": data.get("extracted") or [],
            "missing_fields": data.get("missing_fields") or [],
            "contradictions": data.get("contradictions") or [],
        }
    except json.JSONDecodeError:
        return _heuristic_extract(last_turns, profile_partial, asked_questions)


def _has_openai() -> bool:
    import os
    return bool(os.getenv("OPENAI_API_KEY"))


def _heuristic_extract(
    last_turns: list[dict[str, str]],
    profile_partial: dict,
    asked_questions: list[str],
) -> dict[str, Any]:
    extracted: list[dict[str, Any]] = []
    text = _collect_user_text(last_turns)
    if not text:
        return {"extracted": [], "missing_fields": [], "contradictions": []}

    label_fields = _label_override(_last_user_message(last_turns))
    if label_fields:
        return {"extracted": label_fields, "missing_fields": [], "contradictions": []}

    def _looks_like_gibberish(raw: str) -> bool:
        clean = re.sub(r"\s+", " ", raw.strip().lower())
        if len(clean) < 4:
            return False
        letters = [c for c in clean if c.isalpha()]
        if len(letters) < 5:
            return False
        vowels = sum(1 for c in letters if c in _VOWELS)
        vowel_ratio = vowels / max(len(letters), 1)
        tokens = re.findall(r"[a-zàâäéèêëîïôöùûüÿ]+", clean)
        if any(t in _COMMON_WORDS for t in tokens):
            return False
        return vowel_ratio < 0.2

    if _looks_like_gibberish(text):
        extracted.append({"field": "goal_confidence", "value": 0.1, "confidence": 0.9, "source_quote": ""})
        extracted.append({"field": "project_type", "value": None, "confidence": 0.9, "source_quote": ""})
        extracted.append({"field": "project_type_confidence", "value": 0.1, "confidence": 0.9, "source_quote": ""})
        return {"extracted": extracted, "missing_fields": [], "contradictions": []}

    # Risque Q_RISK_CALIB : A→6–7, B→2–3, C→4–5 (priorité si q_risk/Q_RISK_CALIB demandé ou message très court)
    risk_requested = "Q_RISK_CALIB" in asked_questions or "q_risk" in asked_questions
    budget_single_requested = "q_budget_single" in asked_questions
    if risk_requested or len(text.strip()) <= 25:
        if _RISK_ONLY_A.search(text.strip()) or _RISK_A_RE.search(text):
            extracted.append({"field": "risk_tolerance_score", "value": 6.5, "confidence": 0.9, "source_quote": "A"})
        elif _RISK_ONLY_B.search(text.strip()) or _RISK_B_RE.search(text):
            extracted.append({"field": "risk_tolerance_score", "value": 2.5, "confidence": 0.9, "source_quote": "B"})
        elif _RISK_ONLY_C.search(text.strip()) or _RISK_C_RE.search(text):
            extracted.append({"field": "risk_tolerance_score", "value": 4.5, "confidence": 0.9, "source_quote": "C"})

    # Effort régulier (mensuel)
    mm = _MONTHLY_RE.search(text.replace("\u202f", " "))
    if mm:
        raw = mm.group(1).replace(" ", "").replace(".", "").replace(",", ".")
        try:
            val = float(raw)
            if 1 <= val <= 100000:
                extracted.append({"field": "monthly_contribution", "value": val, "confidence": 0.85, "source_quote": mm.group(0)})
                extracted.append({"field": "contribution_frequency", "value": "monthly", "confidence": 0.85, "source_quote": mm.group(0)})
        except ValueError:
            pass

    # Effort régulier (hebdo)
    wm = _WEEKLY_RE.search(text.replace("\u202f", " "))
    if wm:
        raw = wm.group(1).replace(" ", "").replace(".", "").replace(",", ".")
        try:
            val = float(raw)
            if 1 <= val <= 100000:
                extracted.append({"field": "monthly_contribution", "value": val, "confidence": 0.8, "source_quote": wm.group(0)})
                extracted.append({"field": "contribution_frequency", "value": "weekly", "confidence": 0.8, "source_quote": wm.group(0)})
        except ValueError:
            pass

    # Montant cible
    m = _AMOUNT_RE.search(text.replace("\u202f", " "))
    if m:
        raw = m.group(1).replace(" ", "").replace(".", "").replace(",", ".")
        try:
            val = float(raw)
            if val >= 100:  # plausibly target_amount
                extracted.append({
                    "field": "goal.target_amount",
                    "value": val,
                    "confidence": 0.85,
                    "source_quote": m.group(0),
                })
        except ValueError:
            pass

    # Mise initiale (capital au départ, X au début)
    for pat, label in [
        (re.compile(r"(\d{1,3}(?:[\s.,]\d{3})*|\d+)\s*(?:€|eur|euros?)?\s*au\s*d[ée]part", re.I), "au départ"),
        (re.compile(r"capital\s*(?:de|à)?\s*(\d{1,3}(?:[\s.,]\d{3})*|\d+)\s*(?:€|eur|euros?)?", re.I), "capital"),
    ]:
        pm = pat.search(text.replace("\u202f", " "))
        if pm:
            raw = (pm.group(1) or pm.group(0)).replace(" ", "").replace(".", "").replace(",", ".")
            try:
                val = float(raw)
                if 100 <= val <= 10000000:
                    extracted.append({"field": "initial_amount", "value": val, "confidence": 0.85, "source_quote": pm.group(0)})
                    break
            except (ValueError, TypeError):
                pass

    if _NO_INITIAL_RE.search(text):
        extracted.append({"field": "initial_amount", "value": 0, "confidence": 0.8, "source_quote": "rien au départ"})

    # Budget unique: montant sans fréquence -> fréquence mensuelle déduite (confiance moyenne)
    if budget_single_requested and not mm and not wm:
        fm = _AMOUNT_RE.search(text.replace("\u202f", " "))
        if fm:
            raw = fm.group(1).replace(" ", "").replace(".", "").replace(",", ".")
            try:
                val = float(raw)
                if 1 <= val <= 100000:
                    extracted.append({"field": "monthly_contribution", "value": val, "confidence": 0.6, "source_quote": fm.group(0)})
                    extracted.append({"field": "contribution_frequency", "value": "monthly", "confidence": 0.6, "source_quote": fm.group(0)})
            except ValueError:
                pass

    # Budget unique: mention vague (sans montant)
    if budget_single_requested and _VAGUE_AMOUNT_RE.search(text):
        if _INITIAL_HINT_RE.search(text):
            extracted.append({"field": "initial_amount", "value": None, "confidence": 0.3, "source_quote": "vague"})
        if _REGULAR_HINT_RE.search(text):
            freq = "monthly" if _FREQ_MONTHLY_RE.search(text) else "weekly" if _FREQ_WEEKLY_RE.search(text) else None
            extracted.append({"field": "monthly_contribution", "value": None, "confidence": 0.3, "source_quote": "vague"})
            if freq:
                extracted.append({"field": "contribution_frequency", "value": freq, "confidence": 0.4, "source_quote": "vague"})

    if _NO_MONTHLY_RE.search(text):
        extracted.append({"field": "monthly_contribution", "value": 0, "confidence": 0.8, "source_quote": "rien régulier"})

    # Horizon en années
    ym = _YEARS_RE.search(text)
    if ym:
        y = int(ym.group(1))
        months = y * 12
        if 1 <= months <= 600:
            extracted.append({
                "field": "horizon_months",
                "value": months,
                "confidence": 0.9,
                "source_quote": ym.group(0),
            })
            if months <= 36:
                extracted.append({"field": "horizon_bucket", "value": "short", "confidence": 0.85, "source_quote": ym.group(0)})
            elif months <= 84:
                extracted.append({"field": "horizon_bucket", "value": "medium", "confidence": 0.85, "source_quote": ym.group(0)})
            else:
                extracted.append({"field": "horizon_bucket", "value": "long", "confidence": 0.85, "source_quote": ym.group(0)})

    # Horizon en mois
    mm = _MONTHS_RE.search(text)
    if mm and not ym:
        mo = int(mm.group(1))
        if 1 <= mo <= 600:
            extracted.append({
                "field": "horizon_months",
                "value": mo,
                "confidence": 0.9,
                "source_quote": mm.group(0),
            })

    # project_type depuis mots-clés
    existing_conf = profile_partial.get("project_type_confidence")
    try:
        existing_conf = float(existing_conf) if existing_conf is not None else None
    except (TypeError, ValueError):
        existing_conf = None
    if existing_conf is None or existing_conf < 0.7:
        project_matches: list[tuple[str, str]] = []
        low = text.lower()
        for ptype, buckets in _PROJECT_TYPE_KEYWORDS.items():
            for kw in buckets.get("strong", []):
                if kw in low:
                    project_matches.append((ptype, kw))
            for kw in buckets.get("weak", []):
                if kw in low:
                    project_matches.append((ptype, kw))

        project_type = None
        project_conf = None
        project_source = None
        if project_matches:
            types = {t for t, _ in project_matches}
            if len(types) == 1:
                project_type = project_matches[0][0]
                project_source = project_matches[0][1]
                if any(kw in low for kw in _PROJECT_TYPE_KEYWORDS[project_type].get("strong", [])):
                    project_conf = 0.9
                else:
                    project_conf = 0.7
            else:
                project_type = "other"
                project_conf = 0.4
        else:
            project_type = "other"
            project_conf = 0.2

        if project_type and project_conf is not None:
            extracted.append({"field": "project_type", "value": project_type, "confidence": project_conf, "source_quote": project_source or ""})
            extracted.append({"field": "project_type_confidence", "value": project_conf, "confidence": 0.9, "source_quote": project_source or ""})
            extracted.append({"field": "goal_confidence", "value": project_conf, "confidence": 0.9, "source_quote": project_source or ""})
            if project_conf >= 0.7:
                extracted.append({"field": "goal_locked", "value": True, "confidence": 0.9, "source_quote": project_source or ""})
            if project_source:
                extracted.append({"field": "project_type_source", "value": project_source, "confidence": 0.9, "source_quote": project_source})

    # goal.type depuis mots-clés + sync project_type si applicable
    low = text.lower()
    goal_type_val = None
    if any(w in low for w in ["apport", "apport pour", "acheter", "immobilier", "maison", "appart", "voiture"]):
        goal_type_val = "buy_something"
        extracted.append({"field": "goal.type", "value": "apport", "confidence": 0.8, "source_quote": ""})
    elif any(w in low for w in ["retraite", "long terme"]):
        goal_type_val = "prepare_future"
        extracted.append({"field": "goal.type", "value": "retraite", "confidence": 0.8, "source_quote": ""})
    elif any(w in low for w in ["précaution", "precaution", "sécurité", "security"]):
        goal_type_val = "protect_family"
        extracted.append({"field": "goal.type", "value": "precaution", "confidence": 0.8, "source_quote": ""})

    if goal_type_val:
        extracted.append({"field": "project_type", "value": goal_type_val, "confidence": 0.8, "source_quote": ""})
        extracted.append({"field": "project_type_confidence", "value": 0.8, "confidence": 0.9, "source_quote": ""})
        extracted.append({"field": "project_type_source", "value": "goal_type", "confidence": 0.9, "source_quote": ""})
        extracted.append({"field": "goal_confidence", "value": 0.8, "confidence": 0.9, "source_quote": ""})
        extracted.append({"field": "goal_locked", "value": True, "confidence": 0.9, "source_quote": ""})

    # risk bucket (mots-clés) — seulement si pas déjà extrait via A/B/C
    if not any(e.get("field") == "risk_tolerance_score" for e in extracted):
        if any(w in low for w in ["stabilité", "stable", "conservateur", "sécurit"]):
            extracted.append({"field": "risk_tolerance_score", "value": 3, "confidence": 0.75, "source_quote": ""})
        elif any(w in low for w in ["équilibré", "equilibre", "moitié"]):
            extracted.append({"field": "risk_tolerance_score", "value": 5, "confidence": 0.75, "source_quote": ""})
        elif any(w in low for w in ["croissance", "dynamique", "variation"]):
            extracted.append({"field": "risk_tolerance_score", "value": 7, "confidence": 0.75, "source_quote": ""})

    # Besoin de retrait / souplesse d'épargne (liquidity_needs)
    liquidity_value = None
    liquidity_conf = None
    if _LIQUIDITY_NEGATIVE_RE.search(text):
        liquidity_value, liquidity_conf = "low", 0.8
    elif _LIQUIDITY_WITHDRAW_RE.search(text) and _LIQUIDITY_HIGH_RE.search(text):
        liquidity_value, liquidity_conf = "high", 0.8
    elif _LIQUIDITY_WITHDRAW_RE.search(text) and _LIQUIDITY_FLEX_RE.search(text):
        liquidity_value, liquidity_conf = "medium", 0.75
    elif _LIQUIDITY_FLEX_RE.search(text) and "liquidity_needs" not in profile_partial:
        liquidity_value, liquidity_conf = "medium", 0.7
    if liquidity_value is not None and liquidity_conf is not None:
        extracted.append({"field": "liquidity_needs.value", "value": liquidity_value, "confidence": liquidity_conf, "source_quote": ""})
        extracted.append({"field": "liquidity_needs.confidence", "value": liquidity_conf, "confidence": 0.9, "source_quote": ""})

    return {"extracted": extracted, "missing_fields": [], "contradictions": []}
