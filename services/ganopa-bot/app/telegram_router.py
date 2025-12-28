import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from starlette.responses import JSONResponse

from .config import TELEGRAM_BOT_TOKEN, WEBHOOK_SECRET

logger = logging.getLogger("telegram")

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ganopa-telegram-webhook",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def _verify_webhook_secret(header_value: Optional[str]) -> None:
    # Si tu n’as pas configuré de secret côté Telegram => on ne bloque pas
    if not WEBHOOK_SECRET:
        return
    if not header_value or header_value != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid Telegram secret token")


@router.get("/webhook")
def webhook_get():
    # Juste pour éviter “page blanche” au navigateur
    return {"ok": True, "hint": "Telegram webhook expects POST"}


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    # Telegram header exact:
    x_telegram_bot_api_secret_token: Optional[str] = Header(
        default=None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
):
    # 1) Sécurité optionnelle
    _verify_webhook_secret(x_telegram_bot_api_secret_token)

    # 2) Lecture JSON
    try:
        update: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    update_id = update.get("update_id")
    logger.info("telegram_update_received", extra={"update_id": update_id})

    # 3) Traitement async en background (CRUCIAL)
    background_tasks.add_task(process_telegram_update_safe, update)

    # 4) Réponse IMMÉDIATE à Telegram (sinon timeout)
    return JSONResponse({"ok": True})


# -------------------------------------------------
# Processing (background)
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
    # Message standard
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return

    logger.info("telegram_message", extra={"chat_id": chat_id, "text": text[:120]})

    # Réponse simple (validation pipe)
    if text == "/start":
        reply = "👋 Hello, Ganopa Agent est en ligne."
    elif text:
        reply = f"✅ Reçu: {text}"
    else:
        reply = "✅ Reçu."

    send_telegram_message(chat_id, reply)


def send_telegram_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        with httpx.Client(timeout=10) as client:
            client.post(url, json=payload)
    except Exception as e:
        logger.exception("telegram_send_failed", extra={"chat_id": chat_id, "err": str(e)})
