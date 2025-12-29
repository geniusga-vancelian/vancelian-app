import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from starlette.responses import JSONResponse

from .config import TELEGRAM_BOT_TOKEN, WEBHOOK_SECRET, OPENAI_API_KEY, OPENAI_MODEL

# -------------------------------------------------
# App & logging
# -------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ganopa-bot")

app = FastAPI(title="Ganopa Agent Bot")


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
    if not WEBHOOK_SECRET:
        return
    if not header_value or header_value != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid Telegram secret token")


@app.get("/telegram/webhook")
def telegram_webhook_get():
    return {"ok": True, "hint": "Telegram webhook expects POST"}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: Optional[str] = Header(
        default=None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
):
    _verify_webhook_secret(x_telegram_bot_api_secret_token)

    try:
        update: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    update_id = update.get("update_id")
    logger.info("telegram_update_received", extra={"update_id": update_id})

    # traitement async => Telegram doit avoir une réponse immédiate
    background_tasks.add_task(process_telegram_update_safe, update)
    return JSONResponse({"ok": True})


# -------------------------------------------------
# OpenAI call
# -------------------------------------------------

def call_openai(text: str, *, update_id: Optional[int] = None, chat_id: Optional[int] = None) -> str:
    """
    Réponse IA simple (MVP).
    """
    if not text:
        return "👋 Envoie-moi un message."

    # Logs diagnostics (très utiles pour voir si tu es sur la bonne task/version)
    logger.info(
        "openai_call_start",
        extra={
            "update_id": update_id,
            "chat_id": chat_id,
            "model": OPENAI_MODEL,
            "text_len": len(text),
        },
    )

    if not OPENAI_API_KEY:
        logger.error("openai_missing_api_key", extra={"update_id": update_id, "chat_id": chat_id})
        return "⚠️ OPENAI_API_KEY manquante côté serveur."

    system = (
        "You are Ganopa, a helpful assistant. "
        "Reply in French unless the user writes in another language. "
        "Be concise."
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        "temperature": 0.4,
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )

            logger.info(
                "openai_http_response",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "status": r.status_code,
                },
            )

            if r.status_code >= 400:
                logger.error(
                    "openai_http_error",
                    extra={
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "status": r.status_code,
                        "body": r.text[:500],
                    },
                )
                return "⚠️ OpenAI erreur (HTTP)."

            data = r.json()

            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            logger.info(
                "openai_call_ok",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "model": OPENAI_MODEL,
                    "reply_len": len(content or ""),
                },
            )

            return content or "✅ OK"

    except Exception as e:
        logger.exception(
            "openai_call_failed",
            extra={"update_id": update_id, "chat_id": chat_id, "err": str(e)},
        )
        return "⚠️ OpenAI indisponible."


# -------------------------------------------------
# Processing
# -------------------------------------------------

def process_telegram_update_safe(update: Dict[str, Any]) -> None:
    try:
        process_telegram_update(update)
    except Exception as e:
        logger.exception(
            "telegram_update_processing_failed",
            extra={"update_id": update.get("update_id"), "err": str(e)},
        )


def process_telegram_update(update: Dict[str, Any]) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        logger.info("telegram_update_no_message", extra={"update_id": update.get("update_id")})
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id:
        logger.info("telegram_message_missing_chat_id", extra={"update_id": update.get("update_id")})
        return

    logger.info(
        "telegram_message",
        extra={
            "update_id": update.get("update_id"),
            "chat_id": chat_id,
            "text_preview": text[:120],
            "text_len": len(text),
        },
    )

    reply = call_openai(text, update_id=update.get("update_id"), chat_id=chat_id)
    send_telegram_message(chat_id, reply, update_id=update.get("update_id"))


def send_telegram_message(chat_id: int, text: str, *, update_id: Optional[int] = None) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload)

            logger.info(
                "telegram_send_http_response",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "status": resp.status_code,
                },
            )

            if resp.status_code >= 400:
                logger.error(
                    "telegram_send_failed_http",
                    extra={
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "status": resp.status_code,
                        "body": resp.text[:500],
                    },
                )

            resp.raise_for_status()

    except Exception as e:
        logger.exception(
            "telegram_send_failed",
            extra={"update_id": update_id, "chat_id": chat_id, "err": str(e)},
        )
