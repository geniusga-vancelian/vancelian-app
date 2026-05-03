"""Tests unitaires de l'endpoint voice transcribe — D.1.4.8.

Couvre :
  - Kill-switch `ASSISTANCE_VOICE_WHISPER_ENABLED` (défaut false → 503).
  - Validation taille / vide (400, 413).
  - Forward correct vers `transcribe_audio_with_whisper`.
  - Mapping erreurs Whisper → 502.

Aucune connexion réseau réelle : le module `voice.transcribe_audio_with_whisper`
est entièrement mocké via `unittest.mock.patch`. Les tests se concentrent
sur la **route FastAPI** elle-même (validation, dispatch, codes HTTP).

Convention du projet : pas de Postgres, pas de stack, < 100 ms par test.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.assistance import routes as assistance_routes
from services.assistance.voice import VoiceTranscriptionError
from services.auth.models import AuthContext
from services.auth.dependencies import get_current_user_or_admin


def _build_app_with_route() -> FastAPI:
    """Monte une mini-app FastAPI uniquement avec le router assistance,
    pour pouvoir taper sur `/api/app/assistance/voice/transcribe` sans
    démarrer toute la stack."""
    app = FastAPI()
    app.include_router(assistance_routes.router)
    return app


def _override_auth(app: FastAPI, *, client_id) -> None:
    """Remplace la dépendance d'auth par un AuthContext synthétique."""

    def _fake_auth() -> AuthContext:
        return AuthContext(
            user_id=42,
            email=None,
            role="customer",
            zero_trust_role="customer",
            person_id=uuid4(),
            client_id=client_id,
            jwt_sub_typ="user_id",
        )

    app.dependency_overrides[get_current_user_or_admin] = _fake_auth


def _override_db(app: FastAPI) -> MagicMock:
    """Remplace `get_db` par un Session mocké minimal — `_require_client`
    est patché plus haut donc la session n'est jamais réellement utilisée
    pour des queries dans ces tests."""
    db = MagicMock()
    from database import get_db

    app.dependency_overrides[get_db] = lambda: db
    return db


# ─────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────


def test_voice_transcribe_disabled_by_default_returns_503():
    """Sans `ASSISTANCE_VOICE_WHISPER_ENABLED=true`, on attend un 503
    immédiat sans appel OpenAI — kill-switch côté serveur."""
    app = _build_app_with_route()
    _override_auth(app, client_id=uuid4())
    _override_db(app)

    with patch.object(
        assistance_routes,
        "assistance_voice_whisper_enabled",
        return_value=False,
    ), patch.object(assistance_routes, "_require_client", lambda *_a, **_kw: None):
        client = TestClient(app)
        resp = client.post(
            "/api/app/assistance/voice/transcribe",
            files={"audio": ("voice.m4a", b"fake audio", "audio/m4a")},
        )

    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["detail"]["error"]["code"] == "voice_whisper_disabled"


def test_voice_transcribe_empty_audio_returns_400():
    """Body multipart présent mais fichier vide → 400."""
    app = _build_app_with_route()
    _override_auth(app, client_id=uuid4())
    _override_db(app)

    with patch.object(
        assistance_routes,
        "assistance_voice_whisper_enabled",
        return_value=True,
    ), patch.object(assistance_routes, "_require_client", lambda *_a, **_kw: None):
        client = TestClient(app)
        resp = client.post(
            "/api/app/assistance/voice/transcribe",
            files={"audio": ("voice.m4a", b"", "audio/m4a")},
        )

    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["detail"]["error"]["code"] == "voice_audio_empty"


def test_voice_transcribe_oversize_audio_returns_413():
    """Body > ASSISTANCE_VOICE_MAX_BYTES → 413 sans appel OpenAI."""
    app = _build_app_with_route()
    _override_auth(app, client_id=uuid4())
    _override_db(app)

    big_payload = b"x" * (5 * 1024)  # 5 KB

    with patch.object(
        assistance_routes,
        "assistance_voice_whisper_enabled",
        return_value=True,
    ), patch.object(
        assistance_routes,
        "assistance_voice_max_audio_bytes",
        return_value=1024,  # 1 KB pour forcer le dépassement
    ), patch.object(assistance_routes, "_require_client", lambda *_a, **_kw: None):
        client = TestClient(app)
        resp = client.post(
            "/api/app/assistance/voice/transcribe",
            files={"audio": ("voice.m4a", big_payload, "audio/m4a")},
        )

    assert resp.status_code == 413, resp.text
    body = resp.json()
    assert body["detail"]["error"]["code"] == "voice_audio_too_large"


def test_voice_transcribe_happy_path_returns_transcript():
    """Cas nominal : Whisper retourne du texte → 200 + JSON {transcript}."""
    app = _build_app_with_route()
    _override_auth(app, client_id=uuid4())
    _override_db(app)

    fake_transcript_fn = AsyncMock(return_value="Bonjour Vancelian.")

    with patch.object(
        assistance_routes,
        "assistance_voice_whisper_enabled",
        return_value=True,
    ), patch.object(
        assistance_routes,
        "transcribe_audio_with_whisper",
        new=fake_transcript_fn,
    ), patch.object(assistance_routes, "_require_client", lambda *_a, **_kw: None):
        client = TestClient(app)
        resp = client.post(
            "/api/app/assistance/voice/transcribe",
            files={"audio": ("voice.m4a", b"fake audio bytes", "audio/m4a")},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"transcript": "Bonjour Vancelian."}
    fake_transcript_fn.assert_awaited_once()
    # Vérifie que le content-type et le filename ont bien été propagés.
    kwargs = fake_transcript_fn.await_args.kwargs
    assert kwargs["filename"] == "voice.m4a"
    assert kwargs["content_type"] == "audio/m4a"
    assert kwargs["audio_bytes"] == b"fake audio bytes"
    assert kwargs["language_hint"] == "fr"


def test_voice_transcribe_whisper_failure_returns_502():
    """Exception côté Whisper → 502 sans payload OpenAI brut côté client."""
    app = _build_app_with_route()
    _override_auth(app, client_id=uuid4())
    _override_db(app)

    fake_transcript_fn = AsyncMock(
        side_effect=VoiceTranscriptionError("openai status=429"),
    )

    with patch.object(
        assistance_routes,
        "assistance_voice_whisper_enabled",
        return_value=True,
    ), patch.object(
        assistance_routes,
        "transcribe_audio_with_whisper",
        new=fake_transcript_fn,
    ), patch.object(assistance_routes, "_require_client", lambda *_a, **_kw: None):
        client = TestClient(app)
        resp = client.post(
            "/api/app/assistance/voice/transcribe",
            files={"audio": ("voice.m4a", b"fake audio", "audio/m4a")},
        )

    assert resp.status_code == 502, resp.text
    body = resp.json()
    assert body["detail"]["error"]["code"] == "voice_transcribe_failed"
    # Pas de leak du message OpenAI brut (status=429) dans le body client.
    assert "429" not in resp.text


def test_voice_transcribe_octet_stream_falls_back_to_audio_m4a():
    """Certains clients (iOS) envoient `application/octet-stream` →
    on doit retomber sur `audio/m4a` pour que Whisper décode."""
    app = _build_app_with_route()
    _override_auth(app, client_id=uuid4())
    _override_db(app)

    fake_transcript_fn = AsyncMock(return_value="ok")

    with patch.object(
        assistance_routes,
        "assistance_voice_whisper_enabled",
        return_value=True,
    ), patch.object(
        assistance_routes,
        "transcribe_audio_with_whisper",
        new=fake_transcript_fn,
    ), patch.object(assistance_routes, "_require_client", lambda *_a, **_kw: None):
        client = TestClient(app)
        resp = client.post(
            "/api/app/assistance/voice/transcribe",
            files={
                "audio": ("voice.m4a", b"abc", "application/octet-stream"),
            },
        )

    assert resp.status_code == 200
    assert fake_transcript_fn.await_args.kwargs["content_type"] == "audio/m4a"


# ─────────────────────────────────────────────────────────────────────
# Configuration helpers (sanity checks sur la lecture d'env)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("0", False),
        ("", False),
        ("garbage", False),
    ],
)
def test_voice_whisper_enabled_env_parsing(value, expected, monkeypatch):
    from services.assistance import config as assistance_config

    monkeypatch.setenv("ASSISTANCE_VOICE_WHISPER_ENABLED", value)
    assert assistance_config.assistance_voice_whisper_enabled() is expected


def test_voice_whisper_enabled_unset_defaults_false(monkeypatch):
    from services.assistance import config as assistance_config

    monkeypatch.delenv("ASSISTANCE_VOICE_WHISPER_ENABLED", raising=False)
    assert assistance_config.assistance_voice_whisper_enabled() is False
