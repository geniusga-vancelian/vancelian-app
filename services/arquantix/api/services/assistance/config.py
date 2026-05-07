"""Config minimale du service Assistance (OpenAI + rate limit).

OPENAI_API_KEY / OPENAI_MODEL / OPENAI_BASE_URL sont mutualisés avec les autres
services AI (chatbot_epargne, ai_email…) via `os.getenv` — la clé doit être
présente dans `.env` du conteneur Python.
"""

from __future__ import annotations

import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("ASSISTANCE_OPENAI_MODEL") or os.getenv(
    "OPENAI_MODEL", "gpt-4o-mini"
)
OPENAI_BASE_URL = (
    os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
).rstrip("/")


def assistance_rate_limit() -> tuple[int, float]:
    """Quota par client : `ASSISTANCE_RL_MAX` requêtes / `ASSISTANCE_RL_WINDOW_SEC`."""
    try:
        max_n = max(1, int(os.getenv("ASSISTANCE_RL_MAX", "30")))
    except ValueError:
        max_n = 30
    try:
        window = max(1.0, float(os.getenv("ASSISTANCE_RL_WINDOW_SEC", "60")))
    except ValueError:
        window = 60.0
    return max_n, window


def assistance_history_max_turns() -> int:
    """Nombre maximum de tours injectés au prompt OpenAI (limite contexte)."""
    try:
        return max(2, int(os.getenv("ASSISTANCE_HISTORY_MAX_TURNS", "20")))
    except ValueError:
        return 20


def assistance_temperature() -> float:
    try:
        return max(0.0, min(2.0, float(os.getenv("ASSISTANCE_TEMPERATURE", "0.7"))))
    except ValueError:
        return 0.7


# ─────────────────────────────────────────────────────────────────────────────
# Voice input (D.1.4.8)
# ─────────────────────────────────────────────────────────────────────────────
#
# Côté mobile, le moteur de transcription est sélectionné via la variable
# Dart `ASSISTANCE_VOICE_ENGINE` (`native` par défaut, ou `whisper`).
#
# Quand le moteur `whisper` est utilisé, le mobile envoie l'audio à
# l'endpoint POST /api/app/assistance/voice/transcribe qui forward
# vers l'API OpenAI Whisper.
#
# Le kill-switch ci-dessous permet à l'opérateur de désactiver côté
# serveur l'endpoint Whisper sans toucher aux clients (utile en cas de
# problème de coût ou de latence). Les clients tomberont alors sur une
# erreur 503 et l'UI mobile pourra afficher une bascule sur le moteur
# natif.


def assistance_voice_whisper_enabled() -> bool:
    """Active / désactive l'endpoint Whisper côté serveur.

    Défaut : **false** (l'endpoint répond 503). On exige une activation
    explicite via `ASSISTANCE_VOICE_WHISPER_ENABLED=true` dans
    `.env.arquantix` parce que Whisper a un coût par minute et qu'on
    ne veut pas l'allumer par mégarde dans tous les environnements.
    """
    raw = (os.getenv("ASSISTANCE_VOICE_WHISPER_ENABLED") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def assistance_voice_whisper_model() -> str:
    """Modèle Whisper à utiliser. Défaut : `whisper-1` (le seul modèle
    GA OpenAI à la rédaction). Permet de passer plus tard à un modèle
    plus rapide / moins cher sans changer le code."""
    return os.getenv("ASSISTANCE_VOICE_WHISPER_MODEL") or "whisper-1"


def assistance_voice_max_audio_bytes() -> int:
    """Taille max du fichier audio uploadé. Défaut : 10 MB
    (largement suffisant pour ~10 min d'audio AAC à 16 kHz mono).
    OpenAI Whisper accepte jusqu'à 25 MB."""
    try:
        return max(64 * 1024, int(os.getenv("ASSISTANCE_VOICE_MAX_BYTES", str(10 * 1024 * 1024))))
    except ValueError:
        return 10 * 1024 * 1024


def assistance_conversation_state_debug() -> bool:
    """Log une ligne compacte ``conversation_state`` (débogage hors prod)."""
    raw = (
        os.getenv("ASSISTANCE_CONVERSATION_STATE_DEBUG") or ""
    ).strip().lower()
    return raw in {"1", "true", "yes", "on"}
