"""
Ganopa Telegram Bot - Production-ready FastAPI service.

Receives Telegram webhooks and responds using OpenAI.
Deployed on AWS ECS Fargate.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from starlette.responses import JSONResponse

from .config import (
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_SECRET,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    BOT_SIGNATURE_TEST,
)

# -------------------------------------------------
# Build ID - Generated at startup
# -------------------------------------------------

# Generate build ID from timestamp (format: YYYYMMDD-HHMMSS)
_BUILD_TIMESTAMP = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
BOT_BUILD_ID = f"build-{_BUILD_TIMESTAMP}"

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
        "service": "ganopa-bot",
        "bot_build_id": BOT_BUILD_ID,
        "openai_model": OPENAI_MODEL,
        "has_openai_key": bool(OPENAI_API_KEY),
        "has_webhook_secret": bool(WEBHOOK_SECRET),
        "signature_test_mode": BOT_SIGNATURE_TEST,
    },
)


# -------------------------------------------------
# Healthcheck
# -------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ganopa-bot",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


# -------------------------------------------------
# Telegram Webhook
# -------------------------------------------------

def _verify_webhook_secret(header_value: Optional[str]) -> None:
    """Verify Telegram webhook secret token if configured."""
    if not WEBHOOK_SECRET:
        return
    if not header_value or header_value != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid Telegram secret token")


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
    # Verify webhook secret if configured
    _verify_webhook_secret(x_telegram_bot_api_secret_token)

    # Parse JSON payload
    try:
        update: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.error("telegram_webhook_invalid_json", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    update_id = update.get("update_id")
    logger.info(
        "telegram_update_received",
        extra={
            "update_id": update_id,
            "has_message": "message" in update,
            "has_edited_message": "edited_message" in update,
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
        AI-generated response or fallback message on error
    """
    if not text or not text.strip():
        return "👋 Bonjour ! Comment puis-je vous aider aujourd'hui ?"

    text = text.strip()

    logger.info(
        "openai_call_start",
        extra={
            "update_id": update_id,
            "chat_id": chat_id,
            "model": OPENAI_MODEL,
            "text_len": len(text),
            "text_preview": text[:100],
        },
    )

    if not OPENAI_API_KEY:
        logger.error(
            "openai_missing_api_key",
            extra={"update_id": update_id, "chat_id": chat_id},
        )
        return "⚠️ Configuration manquante côté serveur. Veuillez contacter le support."

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

    start_time = time.time()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )

            latency_ms = int((time.time() - start_time) * 1000)

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
                    "openai_http_error",
                    extra={
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "status_code": response.status_code,
                        "error_body": error_body,
                        "latency_ms": latency_ms,
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
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "openai_request_done",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "model": OPENAI_MODEL,
                    "response_len": len(content),
                    "reply_preview": content[:100],
                    "tokens_used": tokens_used,
                    "latency_ms": latency_ms,
                },
            )

            return content

    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "openai_timeout",
            extra={
                "update_id": update_id,
                "chat_id": chat_id,
                "latency_ms": latency_ms,
            },
        )
        return "⚠️ Délai d'attente dépassé. Veuillez réessayer."

    except httpx.NetworkError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "openai_network_error",
            extra={
                "update_id": update_id,
                "chat_id": chat_id,
                "error": str(e),
                "latency_ms": latency_ms,
            },
        )
        return "⚠️ Problème de connexion. Veuillez réessayer dans quelques instants."

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.exception(
            "openai_request_error",
            extra={
                "update_id": update_id,
                "chat_id": chat_id,
                "error": str(e),
                "error_type": type(e).__name__,
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

    if not chat_id:
        logger.info(
            "telegram_message_missing_chat_id",
            extra={"update_id": update.get("update_id")},
        )
        return

    logger.info(
        "telegram_message_processing",
        extra={
            "update_id": update.get("update_id"),
            "chat_id": chat_id,
            "text_len": len(text),
            "text_preview": text[:100],
        },
    )

    # Signature test mode: if enabled, respond with version test message
    if BOT_SIGNATURE_TEST:
        reply = f"✅ VERSION-TEST-123 | {BOT_BUILD_ID}"
        logger.info(
            "signature_test_response",
            extra={
                "update_id": update.get("update_id"),
                "chat_id": chat_id,
                "bot_build_id": BOT_BUILD_ID,
            },
        )
    else:
        # Normal mode: call OpenAI to generate response
        # NEVER echo user input - always use OpenAI
        logger.info(
            "openai_request_start",
            extra={
                "update_id": update.get("update_id"),
                "chat_id": chat_id,
                "text_preview": text[:100],
            },
        )
        
        reply = call_openai(
            text,
            update_id=update.get("update_id"),
            chat_id=chat_id,
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

            logger.info(
                "telegram_send_response",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "status_code": response.status_code,
                    "response_len": len(text),
                },
            )

            if response.status_code >= 400:
                error_body = response.text[:500]
                logger.error(
                    "telegram_send_failed_http",
                    extra={
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "status_code": response.status_code,
                        "error_body": error_body,
                    },
                )
                return

            # Verify success
            response.raise_for_status()

            logger.info(
                "telegram_send_done",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                },
            )

    except httpx.TimeoutException:
        logger.error(
            "telegram_send_timeout",
            extra={"update_id": update_id, "chat_id": chat_id},
        )

    except Exception as e:
        logger.exception(
            "telegram_send_exception",
            extra={"update_id": update_id, "chat_id": chat_id, "error": str(e)},
        )
