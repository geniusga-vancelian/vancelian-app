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
import uuid
from collections import OrderedDict
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
    DOCS_DIR,
    DOCS_REFRESH_SECONDS,
    MEMORY_TTL_SECONDS,
    MEMORY_MAX_MESSAGES,
)
from .telegram_handlers import (
    parse_update,
    route_command,
    truncate_message,
    MAX_MESSAGE_LENGTH,
)
from .agent_service import build_messages, call_openai, format_reply
from .memory_store import MemoryStore
from .doc_store import load_docs

# -------------------------------------------------
# Version Identification
# -------------------------------------------------

# Generate a stable version hash based on service name and build ID
VERSION_HASH = hashlib.sha256(f"{SERVICE_NAME}-{BUILD_ID}".encode()).hexdigest()[:8]
VERSION = f"{SERVICE_NAME}-{VERSION_HASH}"

# Set VERSION in telegram_handlers module (after VERSION is defined)
from . import telegram_handlers
telegram_handlers.VERSION = VERSION

# Export VERSION for telegram_handlers
import sys
sys.modules[__name__].VERSION = VERSION

# Get hostname for metadata
try:
    HOSTNAME = socket.gethostname()
except Exception:
    HOSTNAME = "unknown"

# Initialize memory store
_memory_store = MemoryStore(ttl_seconds=MEMORY_TTL_SECONDS, max_messages=MEMORY_MAX_MESSAGES)

# -------------------------------------------------
# Deduplication Cache (in-memory, 5 minutes TTL)
# -------------------------------------------------

# Simple in-memory cache for update_id deduplication
# Format: {update_id: timestamp}
_update_cache: OrderedDict[int, float] = OrderedDict()
_cache_ttl = 300  # 5 minutes in seconds
_cache_max_size = 10000  # Prevent unbounded growth


def _is_duplicate_update(update_id: int) -> bool:
    """
    Check if an update_id has been processed recently.
    Returns True if duplicate, False otherwise.
    Also cleans old entries.
    """
    current_time = time.time()
    
    # Clean old entries (older than TTL)
    cutoff_time = current_time - _cache_ttl
    keys_to_remove = [
        uid for uid, ts in _update_cache.items() if ts < cutoff_time
    ]
    for uid in keys_to_remove:
        _update_cache.pop(uid, None)
    
    # Check if update_id exists
    if update_id in _update_cache:
        return True
    
    # Add to cache
    _update_cache[update_id] = current_time
    
    # Prevent unbounded growth (remove oldest if needed)
    if len(_update_cache) > _cache_max_size:
        _update_cache.popitem(last=False)  # Remove oldest
    
    return False


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
    
    # Load docs to get current hash
    docs_text, docs_hash = load_docs(DOCS_DIR, refresh_seconds=DOCS_REFRESH_SECONDS)
    docs_loaded = bool(docs_text)
    
    # Get memory stats
    memory_stats = _memory_store.stats()
    
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "build_id": BUILD_ID,
        "hostname": HOSTNAME,
        "openai_model": OPENAI_MODEL,
        "has_openai_key": bool(OPENAI_API_KEY),
        "has_webhook_secret": bool(WEBHOOK_SECRET),
        "docs_hash": docs_hash,
        "docs_loaded": docs_loaded,
        "memory_enabled": True,
        "memory_ttl_seconds": MEMORY_TTL_SECONDS,
        "memory_max_messages": MEMORY_MAX_MESSAGES,
        "memory_active_chats": memory_stats["active_chats"],
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
    # Generate correlation_id (use update_id if available, otherwise UUID)
    correlation_id = str(uuid.uuid4())[:8]
    
    # Log webhook reception
    path = str(request.url.path)
    logger.info(
        "webhook_received",
        extra={
            "correlation_id": correlation_id,
            "path": path,
        },
    )
    
    # Verify webhook secret
    header_present, header_ok = _verify_webhook_secret(x_telegram_bot_api_secret_token)
    logger.info(
        "secret_ok",
        extra={
            "correlation_id": correlation_id,
            "header_present": header_present,
            "secret_ok": header_ok,
        },
    )
    
    if not header_ok:
        raise HTTPException(status_code=401, detail="Invalid Telegram secret token")
    
    # Parse JSON payload
    try:
        update: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.error(
            "update_parse_error",
            extra={
                "correlation_id": correlation_id,
                "path": path,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extract update_id and use it as correlation_id if available
    update_id = update.get("update_id")
    if update_id is not None:
        correlation_id = f"upd-{update_id}"
    
    logger.info(
        "update_parsed",
        extra={
            "correlation_id": correlation_id,
            "update_id": update_id,
        },
    )

    # Schedule background processing
    # Telegram requires immediate 200 OK response (within 5 seconds)
    background_tasks.add_task(process_telegram_update_safe, update, correlation_id)

    # Return immediate response to Telegram
    return JSONResponse({"ok": True})


# -------------------------------------------------
# OpenAI Integration
# -------------------------------------------------

def call_openai(
    text: str,
    *,
    correlation_id: str,
    update_id: Optional[int] = None,
    chat_id: Optional[int] = None,
) -> str:
    """
    Call OpenAI API to generate a response.
    
    Args:
        text: User message text
        correlation_id: Correlation ID for logging
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
            "openai_error",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
                "chat_id": chat_id,
                "error": "missing_api_key",
            },
        )
        return "⚠️ OPENAI_API_KEY manquante (backend config)."

    # Log before OpenAI call
    start_time = time.time()
    logger.info(
        "openai_called",
        extra={
            "correlation_id": correlation_id,
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
        with httpx.Client(timeout=20.0) as client:  # Timeout 20s
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code >= 400:
                error_body = response.text[:500]
                logger.error(
                    "openai_error",
                    extra={
                        "correlation_id": correlation_id,
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
                    "openai_error",
                    extra={
                        "correlation_id": correlation_id,
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "error": "empty_choices",
                    },
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
                    "openai_error",
                    extra={
                        "correlation_id": correlation_id,
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "error": "empty_content",
                    },
                )
                return "⚠️ Je n'ai pas pu générer de réponse. Pouvez-vous reformuler votre question ?"

            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            response_len = len(content)
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log successful OpenAI response
            logger.info(
                "openai_ok",
                extra={
                    "correlation_id": correlation_id,
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "model": OPENAI_MODEL,
                    "response_len": response_len,
                    "tokens_used": tokens_used,
                    "latency_ms": latency_ms,
                    "http_status": response.status_code,
                },
            )

            # Return content (prefix will be added by format_reply if needed)
            return content

    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "openai_error",
            extra={
                "correlation_id": correlation_id,
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
            "openai_error",
            extra={
                "correlation_id": correlation_id,
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
            "openai_error",
            extra={
                "correlation_id": correlation_id,
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

def process_telegram_update_safe(update: Dict[str, Any], correlation_id: str) -> None:
    """
    Safe wrapper for processing Telegram updates.
    Catches all exceptions to prevent background task crashes.
    """
    try:
        process_telegram_update(update, correlation_id)
    except Exception as e:
        logger.exception(
            "telegram_update_processing_failed",
            extra={
                "correlation_id": correlation_id,
                "update_id": update.get("update_id"),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


def process_telegram_update(update: Dict[str, Any], correlation_id: str) -> None:
    """
    Process a Telegram update and send AI-generated response.
    
    Flow: parse -> dedupe -> guard (bot/empty) -> route command -> OpenAI -> send
    """
    update_id = update.get("update_id")
    
    # Deduplication: skip if already processed
    if update_id is not None and _is_duplicate_update(update_id):
        logger.info(
            "update_duplicate",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
            },
        )
        return
    
    # Parse update
    chat_id, text, user_id, is_bot, message_id, parsed_update_id = parse_update(update)
    
    # Guard: ignore messages from bots
    if is_bot:
        logger.info(
            "update_ignored_bot",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
                "user_id": user_id,
            },
        )
        return
    
    # Guard: ignore empty messages
    if not text:
        logger.info(
            "update_ignored_empty",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
                "chat_id": chat_id,
            },
        )
        return
    
    # Guard: require chat_id
    if not chat_id:
        logger.info(
            "message_missing_chat_id",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
            },
        )
        return
    
    # Log message extraction
    logger.info(
        "message_extracted",
        extra={
            "correlation_id": correlation_id,
            "update_id": update_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "message_id": message_id,
            "text_len": len(text),
            "text_preview": text[:50] if text else "",
        },
    )

    # Route command or use OpenAI
    reply = None
    
    # Try command routing first
    command_reply = route_command(
        text,
        correlation_id=correlation_id,
        chat_id=chat_id,
        update_id=update_id,
    )
    
    if command_reply:
        reply = command_reply
        logger.info(
            "command_handled",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
                "chat_id": chat_id,
                "command": text.split()[0] if text else None,
            },
        )
    elif BOT_SIGNATURE_TEST:
        # Signature test mode
        reply = f"✅ VERSION-TEST-123 | {BUILD_ID} | {VERSION}"
        logger.info(
            "signature_test_response",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
                "chat_id": chat_id,
                "build_id": BUILD_ID,
                "version": VERSION,
            },
        )
    else:
        # Normal mode: use agent service with memory and docs
        try:
            # Build messages with memory and docs context
            messages, meta = build_messages(
                chat_id,
                text,
                docs_dir=DOCS_DIR,
                docs_refresh_seconds=DOCS_REFRESH_SECONDS,
            )
            
            # Call OpenAI
            raw_reply = call_openai(messages)
            
            # Format reply (add prefix if fresh context)
            reply = format_reply(raw_reply, meta)
            
            # Store in memory
            _memory_store.append(chat_id, "user", text)
            _memory_store.append(chat_id, "assistant", raw_reply)  # Store without prefix
            
            # Log memory status
            if meta.get("fresh_context", False):
                logger.info(
                    "memory_created",
                    extra={
                        "correlation_id": correlation_id,
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "docs_hash": meta.get("docs_hash", "unknown"),
                    },
                )
            else:
                logger.info(
                    "memory_updated",
                    extra={
                        "correlation_id": correlation_id,
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "memory_messages": meta.get("memory_messages", 0),
                    },
                )
                
        except Exception as e:
            logger.exception(
                "agent_service_error",
                extra={
                    "correlation_id": correlation_id,
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            # Fallback to simple OpenAI call
            reply = call_openai(
                text,
                correlation_id=correlation_id,
                update_id=update_id,
                chat_id=chat_id,
            )

    # Truncate message if too long (after formatting)
    reply = truncate_message(reply)

    # Log before sending to Telegram
    logger.info(
        "telegram_send_start",
        extra={
            "correlation_id": correlation_id,
            "update_id": update_id,
            "chat_id": chat_id,
            "reply_len": len(reply),
            "reply_preview": reply[:50] if reply else "",
        },
    )

    # Send response to Telegram
    send_telegram_message(
        chat_id,
        reply,
        correlation_id=correlation_id,
        update_id=update_id,
    )


def send_telegram_message(
    chat_id: int,
    text: str,
    *,
    correlation_id: str,
    update_id: Optional[int] = None,
) -> None:
    """
    Send a message to Telegram user.
    
    Args:
        chat_id: Telegram chat ID
        text: Message text to send
        correlation_id: Correlation ID for logging
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
                    "telegram_send_error",
                    extra={
                        "correlation_id": correlation_id,
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "status_code": response.status_code,
                        "error_body": error_body,
                        "error_type": "http_error",
                    },
                )
                
                # Also log as telegram_send_failed for consistency
                logger.error(
                    "telegram_send_failed",
                    extra={
                        "correlation_id": correlation_id,
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
                "telegram_sent",
                extra={
                    "correlation_id": correlation_id,
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "status_code": response.status_code,
                },
            )
            
            # Also log as telegram_send_ok for consistency
            logger.info(
                "telegram_send_ok",
                extra={
                    "correlation_id": correlation_id,
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "status_code": response.status_code,
                },
            )

    except httpx.TimeoutException:
        logger.error(
            "telegram_send_error",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
                "chat_id": chat_id,
                "error": "timeout",
                "error_type": "timeout",
            },
        )

    except Exception as e:
        logger.exception(
            "telegram_send_error",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
                "chat_id": chat_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        
        # Also log as telegram_send_failed for consistency
        logger.error(
            "telegram_send_failed",
            extra={
                "correlation_id": correlation_id,
                "update_id": update_id,
                "chat_id": chat_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
