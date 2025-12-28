import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from starlette.responses import JSONResponse

from .config import WEBHOOK_SECRET

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
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    _verify_webhook_secret(x_telegram_bot_api_secret_token)

    try:
        update: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    update_id = update.get("update_id")
    logger.info("telegram_update_received", extra={"update_id": update_id})

    background_tasks.add_task(process_telegram_update_safe, update)

    return JSONResponse({"ok": True})


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
        return

    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if not chat_id:
        return

    if text == "/start":
        logger.info("start_command", extra={"chat_id": chat_id})
        return

    logger.info("message_received", extra={"chat_id": chat_id, "text": text[:120]})
