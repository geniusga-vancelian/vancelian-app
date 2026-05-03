"""Transcription audio via l'API OpenAI Whisper (D.1.4.8).

Module appelé par l'endpoint POST `/api/app/assistance/voice/transcribe`
quand le mobile utilise le moteur `whisper` (cf. `voice_transcriber.dart`
côté Flutter).

Architecture :

    [Mobile Flutter] ──multipart audio.m4a──▶ [Next.js BFF proxy]
                                              │
                                              ▼
                                  [FastAPI /assistance/voice/transcribe]
                                              │
                                              ▼ httpx
                                  [api.openai.com/v1/audio/transcriptions]

On reste volontairement minimal : pas de stockage de l'audio, pas de
log du contenu transcrit (PII potentielle), juste un compteur de durée
+ statut OpenAI pour observabilité.
"""

from __future__ import annotations

import logging

import httpx

from services.assistance.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    assistance_voice_whisper_model,
)

logger = logging.getLogger(__name__)


class VoiceTranscriptionError(Exception):
    """Erreur de l'appel Whisper (réseau, status non-2xx, payload invalide)."""


async def transcribe_audio_with_whisper(
    *,
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    language_hint: str | None = None,
) -> str:
    """Appelle OpenAI Whisper avec le buffer audio fourni.

    Arguments
    ---------
    audio_bytes : contenu binaire du fichier (déjà lu en mémoire — la
        validation de taille a lieu côté caller).
    filename : nom du fichier (juste indicatif pour OpenAI, on garde
        celui envoyé par le mobile, ex. `voice.m4a`).
    content_type : MIME type (ex. `audio/m4a` ou `audio/mp4`). OpenAI
        s'en sert pour décoder.
    language_hint : code ISO-639-1 (`fr`, `en`, …) optionnel. Si fourni,
        accélère la détection. Sinon Whisper auto-détecte.

    Retourne
    --------
    Le texte transcrit (str). Peut être vide si l'audio ne contenait
    pas de parole claire — c'est au caller de gérer ce cas.

    Throws
    ------
    VoiceTranscriptionError si OPENAI_API_KEY manquant, réseau KO,
    ou statut OpenAI non-2xx.
    """
    if not OPENAI_API_KEY:
        raise VoiceTranscriptionError("OPENAI_API_KEY missing")

    url = f"{OPENAI_BASE_URL}/audio/transcriptions"
    model = assistance_voice_whisper_model()

    # multipart/form-data : OpenAI exige `file` (pas `audio`) et `model`.
    # On reste sur le format `text` pour avoir directement la string
    # de transcription, sans wrapper JSON.
    files = {
        "file": (filename, audio_bytes, content_type),
    }
    data: dict[str, str] = {
        "model": model,
        "response_format": "text",
    }
    if language_hint:
        data["language"] = language_hint

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                },
                files=files,
                data=data,
            )
    except httpx.HTTPError as exc:
        logger.warning("assistance.voice whisper_network_error err=%s", exc)
        raise VoiceTranscriptionError(f"openai network error: {exc}") from exc

    if resp.status_code != 200:
        # On log le statut + un extrait du body pour debug, sans le
        # body complet (peut contenir des prompts injectés).
        body_preview = (resp.text or "")[:200]
        logger.warning(
            "assistance.voice whisper_status=%s body=%s",
            resp.status_code,
            body_preview,
        )
        raise VoiceTranscriptionError(
            f"openai status={resp.status_code}"
        )

    # `response_format=text` → corps brut sans JSON.
    transcript = (resp.text or "").strip()
    logger.info(
        "assistance.voice whisper_ok model=%s bytes_in=%d chars_out=%d",
        model,
        len(audio_bytes),
        len(transcript),
    )
    return transcript
