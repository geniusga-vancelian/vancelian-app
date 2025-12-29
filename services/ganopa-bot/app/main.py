"""
Ganopa Telegram Bot - Production-ready FastAPI service.

Receives Telegram webhooks and responds using OpenAI.
Deployed on AWS ECS Fargate.
"""

import hashlib
import logging
import os
import socket
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, Response
from starlette.responses import JSONResponse

from .config import (
    SERVICE_NAME,
    BUILD_ID,
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_SECRET,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    BOT_SIGNATURE_TEST,
)

# -------------------------------------------------
# Version Identification
# -------------------------------------------------

# Generate a stable version hash based on service name and build ID
VERSION_HASH = hashlib.sha256(f"{SERVICE_NAME}-{BUILD_ID}".encode()).hexdigest()[:8]
VERSION = f"{SERVICE_NAME}-{VERSION_HASH}"

# Get hostname for metadata
try:
    HOSTNAME = socket.gethostname()
except Exception:
    HOSTNAME = "unknown"

# -------------------------------------------------
# App & logging
# -------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ganopa-bot")

app = FastAPI(title="Ganopa Agent Bot")

# Log startup with comprehensive version identifier
logger.info(
    "ganopa_bot_started",
    extra={
        "service": SERVICE_NAME,
        "version": VERSION,
        "build_id": BUILD_ID,
        "hostname": HOSTNAME,
        "openai_model": OPENAI_MODEL,
        "has_openai_key": bool(OPENAI_API_KEY),
        "has_webhook_secret": bool(WEBHOOK_SECRET),
    },
)


def _add_build_id_header(response: Response) -> Response:
    """Add X-Ganopa-Build-Id and X-Ganopa-Version headers to response."""
    response.headers["X-Ganopa-Build-Id"] = BUILD_ID
    response.headers["X-Ganopa-Version"] = VERSION
    return response


# -------------------------------------------------
# Healthcheck & Meta
# -------------------------------------------------

@app.get("/health")
def health(response: Response):
    """Health check endpoint."""
    _add_build_id_header(response)
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "ts": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/_meta")
def meta(response: Response):
    """Metadata endpoint to verify deployed version and configuration."""
    _add_build_id_header(response)
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "build_id": BUILD_ID,
        "hostname": HOSTNAME,
        "openai_model": OPENAI_MODEL,
        "has_openai_key": bool(OPENAI_API_KEY),
        "has_webhook_secret": bool(WEBHOOK_SECRET),
        "ts": datetime.utcnow().isoformat() + "Z",
    }


# -------------------------------------------------
# Telegram Webhook
# -------------------------------------------------

def _verify_webhook_secret(header_value: Optional[str]) -> Tuple[bool, bool]:
    """
    Verify Telegram webhook secret token if configured.
    
    Returns:
        (header_present, header_ok)
    """
    header_present = header_value is not None and header_value.strip() != ""
    
    if not WEBHOOK_SECRET:
        # Secret not configured, accept any or no header
        return header_present, True
    
    if not header_value or header_value != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid Telegram secret token")
    
    return header_present, True


@app.get("/telegram/webhook")
def telegram_webhook_get():
    """GET endpoint for webhook URL verification."""
    return {"ok": True, "hint": "Telegram webhook expects POST"}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: Optional[str] = Header(
        default=None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
):
    """
    Telegram webhook endpoint.
    
    Receives updates from Telegram, responds immediately with 200 OK,
    and processes the update asynchronously in background.
    """
    # Log webhook reception with path and secret status
    path = str(request.url.path)
    header_present, header_ok = _verify_webhook_secret(x_telegram_bot_api_secret_token)
    
    # Parse JSON payload
    try:
        update: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.error(
            "telegram_webhook_invalid_json",
            extra={
                "path": path,
                "error": str(e),
                "header_secret_present": header_present,
                "header_secret_ok": header_ok,
            },
        )
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    update_id = update.get("update_id")
    message = update.get("message") or update.get("edited_message")
    chat_id = message.get("chat", {}).get("id") if message else None
    text = (message.get("text") or "").strip() if message else ""

    # Log webhook reception with structured data
    logger.info(
        "telegram_webhook_post",
        extra={
            "update_id": update_id,
            "chat_id": chat_id,
            "text_len": len(text),
            "text_preview": text[:50] if text else "",
            "path": path,
            "header_secret_present": header_present,
            "header_secret_ok": header_ok,
        },
    )

    # Schedule background processing
    # Telegram requires immediate 200 OK response (within 5 seconds)
    background_tasks.add_task(process_telegram_update_safe, update)

    # Return immediate response to Telegram
    return JSONResponse({"ok": True})


# -------------------------------------------------
# OpenAI Integration
# -------------------------------------------------

def call_openai(
    text: str,
    *,
    update_id: Optional[int] = None,
    chat_id: Optional[int] = None,
) -> str:
    """
    Call OpenAI API to generate a response.
    
    Args:
        text: User message text
        update_id: Telegram update ID for logging
        chat_id: Telegram chat ID for logging
    
    Returns:
        AI-generated response with 🤖 prefix or fallback message on error
    """
    if not text or not text.strip():
        return "👋 Bonjour ! Comment puis-je vous aider aujourd'hui ?"

    text = text.strip()

    # Check API key before making request
    if not OPENAI_API_KEY:
        logger.error(
            "openai_missing_api_key",
            extra={"update_id": update_id, "chat_id": chat_id},
        )
        return "⚠️ OPENAI_API_KEY manquante (backend config)."

    # Log before OpenAI call
    start_time = time.time()
    logger.info(
        "openai_request_start",
        extra={
            "update_id": update_id,
            "chat_id": chat_id,
            "model": OPENAI_MODEL,
            "text_len": len(text),
            "text_preview": text[:100],
        },
    )

    system_prompt = (
        "You are Ganopa, a professional AI assistant specialized in fintech. "
        "Reply in French unless the user writes in another language. "
        "Be concise and helpful. Keep responses under 200 words."
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
        "max_tokens": 300,
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=20.0) as client:  # Timeout 20s as requested
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Log HTTP response
            logger.info(
                "openai_http_response",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                },
            )

            if response.status_code >= 400:
                error_body = response.text[:500]
                logger.error(
                    "openai_request_failed",
                    extra={
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "status_code": response.status_code,
                        "error_body": error_body,
                        "latency_ms": latency_ms,
                        "error_type": "http_error",
                    },
                )

                if response.status_code == 401:
                    return "⚠️ Erreur d'authentification API. Veuillez contacter le support."
                elif response.status_code == 429:
                    return "⚠️ Trop de requêtes. Veuillez réessayer dans quelques instants."
                elif response.status_code >= 500:
                    return "⚠️ Service temporairement indisponible. Veuillez réessayer plus tard."
                else:
                    return "⚠️ Erreur lors du traitement de votre demande. Veuillez réessayer."

            data = response.json()

            choices = data.get("choices", [])
            if not choices:
                logger.warning(
                    "openai_empty_choices",
                    extra={"update_id": update_id, "chat_id": chat_id},
                )
                return "⚠️ Réponse vide de l'API. Veuillez reformuler votre question."

            content = (
                choices[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            if not content:
                logger.warning(
                    "openai_empty_content",
                    extra={"update_id": update_id, "chat_id": chat_id},
                )
                return "⚠️ Je n'ai pas pu générer de réponse. Pouvez-vous reformuler votre question ?"

            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            response_len = len(content)
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log successful OpenAI response with all details
            logger.info(
                "openai_request_success",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "model": OPENAI_MODEL,
                    "response_len": response_len,
                    "tokens_used": tokens_used,
                    "latency_ms": latency_ms,
                    "http_status": response.status_code,
                },
            )

            # Add 🤖 prefix to prove it's AI-generated (not echo)
            return f"🤖 {content}"

    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "openai_request_failed",
            extra={
                "update_id": update_id,
                "chat_id": chat_id,
                "error": "timeout",
                "error_type": "timeout",
                "latency_ms": latency_ms,
            },
        )
        return "⚠️ Délai d'attente dépassé. Veuillez réessayer."

    except httpx.NetworkError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "openai_request_failed",
            extra={
                "update_id": update_id,
                "chat_id": chat_id,
                "error": "network_error",
                "error_type": "network_error",
                "error_detail": str(e)[:200],
                "latency_ms": latency_ms,
            },
        )
        return "⚠️ Problème de connexion. Veuillez réessayer dans quelques instants."

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.exception(
            "openai_request_failed",
            extra={
                "update_id": update_id,
                "chat_id": chat_id,
                "error": "unexpected_error",
                "error_type": type(e).__name__,
                "error_detail": str(e)[:200],
                "latency_ms": latency_ms,
            },
        )
        return "⚠️ Erreur inattendue. Veuillez réessayer ou contacter le support."


# -------------------------------------------------
# Message Processing
# -------------------------------------------------

def process_telegram_update_safe(update: Dict[str, Any]) -> None:
    """
    Safe wrapper for processing Telegram updates.
    Catches all exceptions to prevent background task crashes.
    """
    try:
        process_telegram_update(update)
    except Exception as e:
        logger.exception(
            "telegram_update_processing_failed",
            extra={
                "update_id": update.get("update_id"),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


def process_telegram_update(update: Dict[str, Any]) -> None:
    """
    Process a Telegram update and send AI-generated response.
    
    Extracts message, calls OpenAI, and sends response to user.
    NEVER echoes user input - always uses OpenAI or returns explicit error.
    """
    message = update.get("message") or update.get("edited_message")
    if not message:
        logger.info(
            "telegram_update_no_message",
            extra={"update_id": update.get("update_id")},
        )
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    # Log extraction
    logger.info(
        "telegram_message_extracted",
        extra={
            "update_id": update.get("update_id"),
            "chat_id": chat_id,
            "text_len": len(text),
            "text_preview": text[:50] if text else "",
        },
    )

    if not chat_id:
        logger.info(
            "telegram_message_missing_chat_id",
            extra={"update_id": update.get("update_id")},
        )
        return

    # Signature test mode: if enabled, respond with version test message
    if BOT_SIGNATURE_TEST:
        reply = f"✅ VERSION-TEST-123 | {BUILD_ID} | {VERSION}"
        logger.info(
            "signature_test_response",
            extra={
                "update_id": update.get("update_id"),
                "chat_id": chat_id,
                "build_id": BUILD_ID,
                "version": VERSION,
            },
        )
    else:
        # Normal mode: call OpenAI to generate response
        # NEVER echo user input - always use OpenAI
        reply = call_openai(
            text,
            update_id=update.get("update_id"),
            chat_id=chat_id,
        )

    # Log before sending to Telegram
    logger.info(
        "telegram_send_start",
        extra={
            "update_id": update.get("update_id"),
            "chat_id": chat_id,
            "reply_len": len(reply),
            "reply_preview": reply[:50] if reply else "",
        },
    )

    # Send response to Telegram
    send_telegram_message(
        chat_id,
        reply,
        update_id=update.get("update_id"),
    )


def send_telegram_message(
    chat_id: int,
    text: str,
    *,
    update_id: Optional[int] = None,
) -> None:
    """
    Send a message to Telegram user.
    
    Args:
        chat_id: Telegram chat ID
        text: Message text to send
        update_id: Telegram update ID for logging
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)

            if response.status_code >= 400:
                error_body = response.text[:500]
                logger.error(
                    "telegram_send_failed",
                    extra={
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "status_code": response.status_code,
                        "error_body": error_body,
                        "error_type": "http_error",
                    },
                )
                return

            # Verify success
            response.raise_for_status()

            logger.info(
                "telegram_send_success",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "status_code": response.status_code,
                },
            )

    except httpx.TimeoutException:
        logger.error(
            "telegram_send_failed",
            extra={
                "update_id": update_id,
                "chat_id": chat_id,
                "error": "timeout",
                "error_type": "timeout",
            },
        )

    except Exception as e:
        logger.exception(
            "telegram_send_failed",
            extra={
                "update_id": update_id,
                "chat_id": chat_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
