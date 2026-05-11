"""Extraction **déterministe** des signaux métier depuis le libellé utilisateur.

Réutilisable par les tools CAL (agent ``action``) et plus tard par d'autres
agents (ex. Conseil) sans passer par un LLM. Le registre ``INTAKE_EXTRACTORS``
permet d'ajouter de nouvelles intentions (``crypto_sell``, ``deposit``, …)
sans fusionner tous les parsers dans un seul fichier.

Convention : chaque extracteur renvoie un dict JSON‑safe pouvant contenir :
``symbol``, ``amount_from``, ``currency_from``, ``_signals`` (liste motifs).
"""

from __future__ import annotations

import re
from typing import Any, Callable, List, Optional, Sequence

from services.assistance.agents.conversation_continuity import (
    COMPOUND_USER_TURN_MEMORY_KEY,
)


def resolve_intake_user_text(
    *,
    user_message: Optional[str],
    memory_state: Optional[dict[str, Any]],
    recent_turns: Optional[List[Any]],
) -> str:
    """Même logique que le routeur : compound turn > message > dernier user."""
    ms = memory_state if isinstance(memory_state, dict) else {}
    cmp_raw = ms.get(COMPOUND_USER_TURN_MEMORY_KEY)
    if isinstance(cmp_raw, str) and cmp_raw.strip():
        return cmp_raw.strip()
    um = (user_message or "").strip()
    if um:
        return um
    rt = recent_turns or []
    for turn in reversed(rt):
        if isinstance(turn, dict) and turn.get("role") == "user":
            return str(turn.get("content") or "").strip()
    return ""


def _collect_assistant_texts_before_last_user(
    recent_turns: Optional[Sequence[Any]],
    *,
    max_assistant_messages: int = 12,
) -> list[str]:
    """Textes assistant précédant le **dernier** message utilisateur dans l'historique."""
    if not recent_turns:
        return []
    rows = list(recent_turns)
    if not rows:
        return []
    last = rows[-1]
    if not isinstance(last, dict) or last.get("role") != "user":
        return []
    out: list[str] = []
    idx = len(rows) - 2
    while idx >= 0 and len(out) < max_assistant_messages:
        row = rows[idx]
        if isinstance(row, dict) and row.get("role") == "assistant":
            raw = str(row.get("content") or "").strip()
            if raw:
                out.append(raw)
        idx -= 1
    return out


def infer_crypto_symbol_from_recent_turns(
    recent_turns: Optional[Sequence[Any]],
) -> Optional[str]:
    """Déduit BTC/ETH/… depuis les **réponses assistant** avant le dernier user."""
    chunks = _collect_assistant_texts_before_last_user(recent_turns)
    if not chunks:
        return None
    return _detect_symbol(" ".join(chunks))


_BUY_VERB_INTENT_RE = re.compile(
    r"(?is)"
    r"\bachat\b|\bachats\b|\bacheter\b|\binvestir\b|\binvestis\w*\b|\bj'achète\b|"
    r"\bjachete\b|\btrade\b|\btrading\b|\bachet\w*\b|\bbuy\b|\bpurchase\b"
)


def assistant_recent_frames_crypto_buy_intent(
    recent_turns: Optional[Sequence[Any]],
) -> bool:
    """True si les derniers assistants évoquent un achat et un actif connu."""
    chunks = _collect_assistant_texts_before_last_user(recent_turns)
    if not chunks:
        return False
    blob = " ".join(chunks).lower()
    return bool(_BUY_VERB_INTENT_RE.search(blob)) and _detect_symbol(blob) is not None


# ── Registre extensible ───────────────────────────────────────────────────

IntakeExtractor = Callable[[str], dict[str, Any]]

INTAKE_EXTRACTORS: dict[str, IntakeExtractor] = {}


def register_intake_extractor(kind: str, fn: IntakeExtractor) -> None:
    INTAKE_EXTRACTORS[kind] = fn


def extract_intake_signals(kind: str, text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    fn = INTAKE_EXTRACTORS.get(kind)
    if fn is None:
        return {}
    try:
        out = fn(raw)
        return out if isinstance(out, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


# ── Normalisation montants / devises ───────────────────────────────────────

_WS = re.compile(r"\s+", re.MULTILINE)

_RE_SYMBOL_GROUPS: list[tuple[str, re.Pattern[str]]] = [
    ("BTC", re.compile(r"\b(bitcoin|btc)\b", re.I)),
    ("ETH", re.compile(r"\b(ethereum|\beth\b)\b", re.I)),
    ("SOL", re.compile(r"\b(solana|\bsol\b)\b", re.I)),
    ("XRP", re.compile(r"\b(xrp)\b", re.I)),
    ("DOGE", re.compile(r"\b(dogecoin|\bdoge\b)\b", re.I)),
    ("USDC", re.compile(r"\b(usdc)\b", re.I)),
    ("EURC", re.compile(r"\b(eurc)\b", re.I)),
    ("USDT", re.compile(r"\b(usdt)\b", re.I)),
]


def _norm_spaces(s: str) -> str:
    return _WS.sub(" ", (s or "").strip())


def parse_amount_eu_us(text: str) -> Optional[float]:
    """Nombre positif : « 1 000,50 », « 1.234,56 », « 1234.56 », ``1000``."""
    t = text.strip().replace("\u202f", " ").replace("\xa0", " ")
    if not t:
        return None
    t = re.sub(r"^(?:environ|env|~|≈)\s*", "", t, flags=re.I)
    t_spaces = re.sub(r"[\s']", "", t)
    if not t_spaces:
        return None

    comma = "," in t_spaces
    dot = "." in t_spaces
    if comma and dot:
        if t_spaces.rindex(",") > t_spaces.rindex("."):
            canon = t_spaces.replace(".", "").replace(",", ".")
        else:
            canon = t_spaces.replace(",", "")
    elif comma and not dot:
        parts = t_spaces.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            canon = parts[0] + "." + parts[1]
        else:
            canon = t_spaces.replace(",", ".")
    else:
        canon = t_spaces.replace(",", "")

    try:
        v = float(canon)
    except ValueError:
        return None
    return v if v > 0 else None


_RE_EUR = re.compile(
    r"(?:€\s*([\d\s\.,]+)|([\d\s\.,]+)\s*(?:€|eur\.?|\beuro?s?\b))",
    re.I,
)
_RE_USD = re.compile(
    r"(?:\$\s*([\d\s\.,]+)|([\d\s\.,]+)\s*(?:\$|usd|\bdollar?s?\b))",
    re.I,
)
_RE_AMOUNT_NEAR_CCY = re.compile(
    r"\b([\d\s\.,]{1,20})\s*(?:USD|EUR|\$|€|dollar?s?|euro?s?)\b"
    r"|\b(?:USD|EUR|\$|€)\s*([\d\s\.,]{1,20})\b",
    re.I,
)
_RE_AMOUNT_DE_OF = re.compile(
    r"\b(?:pour|de|d')\s*(€\s*)?([\d\s\.,]+(?:[.,]\d{1,2})?)",
    re.I,
)


def _currency_hint(fragment: str) -> Optional[str]:
    u = fragment.upper()
    if re.search(r"€|\bEUR\b|\bEURO", u):
        return "EUR"
    if re.search(r"\$|\bUSD\b|\bDOLL", u):
        return "USD"
    return None


_COMPOUND_USER_TAIL_MARKER = "[DEMANDE / RÉPONSE UTILISATEUR SUR CE TOUR]"


def split_compound_user_tail(text: str) -> tuple[str, str]:
    """Isolée du bloc utilisateur après ``compound_user_turn`` Lot 8.

    Retour ``(assistant_prefix_tail, utilisateur_du_tour)``.
    Sans marqueur : ``("", texte_entier_normalisé)``.
    Aligné textuellement sur ``build_previous_bot_context_block`` /
    ``conversation_continuity`` (sans dépendance circulaire).
    """
    nt = _norm_spaces((text or "").replace("\u2019", "'"))
    key = _COMPOUND_USER_TAIL_MARKER
    i = nt.find(key)
    if i < 0:
        return "", nt
    prefix = nt[:i].strip()
    tail = nt[i + len(key) :].strip()
    return prefix, tail if tail else nt


def _detect_amount_currency_last(text: str) -> tuple[Optional[float], Optional[str]]:
    """Dernière occurrence **dans ce segment** — évite de prendre un « 10 € »
    factice dans l’historique assistant quand le montant réel est sur le dernier bloc user.
    """

    def _take_last_good(
        pat: re.Pattern[str],
        group_fn: Callable[[re.Match[str]], tuple[str, str]],
        fixed_ccy: Optional[str] = None,
    ) -> tuple[Optional[float], Optional[str]]:
        last: tuple[Optional[float], Optional[str]] = (None, None)
        for m in pat.finditer(t):
            raw1, raw2 = group_fn(m)
            raw = (raw1 or raw2 or "").strip()
            if not raw:
                continue
            amt = parse_amount_eu_us(raw)
            if amt is None:
                continue
            ccy = fixed_ccy or _currency_hint(m.group(0))
            last = (amt, ccy)
        return last

    t = _norm_spaces(text or "")
    if not t:
        return None, None

    last = _take_last_good(
        _RE_EUR,
        lambda m: (m.group(1) or "", m.group(2) or ""),
        fixed_ccy="EUR",
    )
    if last[0] is not None:
        return last
    last = _take_last_good(
        _RE_USD,
        lambda m: (m.group(1) or "", m.group(2) or ""),
        fixed_ccy="USD",
    )
    if last[0] is not None:
        return last

    last_match: Optional[re.Match[str]] = None
    for m in _RE_AMOUNT_NEAR_CCY.finditer(t):
        last_match = m
    if last_match is not None:
        raw_amt = last_match.group(1) or last_match.group(2)
        if raw_amt:
            amt = parse_amount_eu_us(raw_amt)
            hint = _currency_hint(last_match.group(0))
            if amt is not None:
                return amt, hint

    last_pf: Optional[re.Match[str]] = None
    for m in _RE_AMOUNT_DE_OF.finditer(t):
        last_pf = m
    if last_pf is not None:
        amt = parse_amount_eu_us(last_pf.group(2))
        hint = _currency_hint(last_pf.group(0))
        if amt is not None:
            return amt, hint or "EUR"
    return None, None


def _detect_amount_currency_compound_safe(text_full: str) -> tuple[Optional[float], Optional[str]]:
    """Montant devise : bloc **USER** après le marqueur Lot 8 d’abord, sinon bloc assistant préfixé."""
    pref, tail = split_compound_user_tail(text_full)
    amt_u, cc_u = _detect_amount_currency_last(tail)
    if amt_u is not None:
        return amt_u, cc_u if cc_u else "EUR"
    if pref.strip():
        return _detect_amount_currency_last(pref)
    return _detect_amount_currency_last(tail)


def _detect_symbol(text: str) -> Optional[str]:
    t = _norm_spaces(text)
    for sym, pat in _RE_SYMBOL_GROUPS:
        if pat.search(t):
            return sym
    return None


def extract_crypto_buy_from_text(text: str) -> dict[str, Any]:
    matched: list[str] = []
    t = _norm_spaces(text.replace("’", "'"))
    pref, tail = split_compound_user_tail(t)
    sym = _detect_symbol(tail) or (
        _detect_symbol(pref) if pref else None
    ) or _detect_symbol(t)
    if sym:
        matched.append(f"symbol:{sym}")
    amt, ccy = _detect_amount_currency_compound_safe(t)
    if amt is not None:
        matched.append(f"amount:{amt}")
    if ccy:
        matched.append(f"currency:{ccy}")
    # EUR implicite (FR + mention crypto / euro)
    if amt is not None and not ccy:
        if re.search(
            r"(?:€|\beuro|\bEUR\b|\bavec\b|\ben\b\s*(?:btc|bitcoin|eth))", t, re.I
        ):
            ccy = "EUR"
            matched.append("currency_implicit_eur")
        else:
            ccy = "EUR"
            matched.append("currency_default_eur")
    out: dict[str, Any] = {"_signals": matched}
    if sym:
        out["symbol"] = sym
    if amt is not None:
        out["amount_from"] = amt
    if ccy:
        out["currency_from"] = str(ccy).upper()[:16]
    return out


register_intake_extractor("crypto_buy", extract_crypto_buy_from_text)


# ── Fusion : priorité au texte utilisateur détecté dans le tour ─────────────


def _coerce_positive_float(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        f = float(raw)
        return f if f > 0 else None
    if isinstance(raw, str) and raw.strip():
        try:
            f = float(raw.replace(",", ".").replace(" ", ""))
        except ValueError:
            return None
        return f if f > 0 else None
    return None


def _norm_symbol(s: Optional[str]) -> Optional[str]:
    if not isinstance(s, str) or not s.strip():
        return None
    return s.strip().upper()[:24]


def _coerce_topic_symbol(topic: Optional[dict[str, Any]]) -> Optional[str]:
    if not isinstance(topic, dict):
        return None
    if str(topic.get("kind") or "").strip().lower() != "instrument":
        return None
    return _norm_symbol(topic.get("instrument_symbol"))


def merge_crypto_buy_intake(
    *,
    tool_symbol: Optional[str],
    tool_amount_from: Optional[Any],
    tool_currency_from: Optional[str],
    signals: dict[str, Any],
    pending_action: Optional[dict[str, Any]],
    current_topic: Optional[dict[str, Any]],
    recent_turns: Optional[Sequence[Any]] = None,
) -> dict[str, Any]:
    """Priorité : texte utilisateur > args outil > brouillon > topic > historique assistant."""
    sig_sym = _norm_symbol(signals.get("symbol"))
    sig_amt = _coerce_positive_float(signals.get("amount_from"))
    sig_ccy = (
        str(signals["currency_from"]).strip().upper()[:16]
        if signals.get("currency_from")
        else None
    )

    ts = _norm_symbol(tool_symbol)
    ta = _coerce_positive_float(tool_amount_from)
    tc = (
        str(tool_currency_from).strip().upper()[:16]
        if isinstance(tool_currency_from, str) and tool_currency_from.strip()
        else None
    )

    pend: dict[str, Any] = pending_action if isinstance(pending_action, dict) else {}
    pk = str(pend.get("target_kind") or "").strip().lower()
    psym = _norm_symbol(pend.get("target_id")) if pk == "crypto_buy" else None
    pa = _coerce_positive_float(pend.get("amount_from"))
    pc = (
        str(pend["currency_from"]).strip().upper()[:16]
        if isinstance(pend.get("currency_from"), str) and str(pend["currency_from"]).strip()
        else None
    )

    topic_sym = _coerce_topic_symbol(current_topic)
    assist_sym = _norm_symbol(infer_crypto_symbol_from_recent_turns(recent_turns))

    symbol = sig_sym or ts or psym or topic_sym or assist_sym
    amount_from = sig_amt or ta or pa
    currency_from = sig_ccy or tc or pc
    if amount_from is not None and not currency_from:
        currency_from = "EUR"

    sym_src: Optional[str]
    if sig_sym:
        sym_src = "text"
    elif ts:
        sym_src = "tool"
    elif psym:
        sym_src = "pending"
    elif topic_sym:
        sym_src = "topic"
    elif assist_sym:
        sym_src = "assistant_history"
    else:
        sym_src = None

    return {
        "symbol": symbol,
        "amount_from": amount_from,
        "currency_from": currency_from,
        "merge_sources": {
            "symbol": sym_src,
            "amount": (
                "text"
                if sig_amt
                else ("tool" if ta else ("pending" if pa else None))
            ),
            "currency": (
                "text"
                if sig_ccy
                else ("tool" if tc else ("pending" if pc else ("default" if currency_from else None)))
            ),
        },
    }


__all__ = [
    "INTAKE_EXTRACTORS",
    "register_intake_extractor",
    "extract_intake_signals",
    "extract_crypto_buy_from_text",
    "infer_crypto_symbol_from_recent_turns",
    "assistant_recent_frames_crypto_buy_intent",
    "merge_crypto_buy_intake",
    "resolve_intake_user_text",
    "parse_amount_eu_us",
    "split_compound_user_tail",
]
