import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from starlette.responses import JSONResponse

from .config import (
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_SECRET,
    VANCELIAN_BACKEND_URL,
    VANCELIAN_INTERNAL_TOKEN,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ganopa-bot")

app = FastAPI(title="Ganopa Agent Bot")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ganopa-bot",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


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

    background_tasks.add_task(process_telegram_update_safe, update)

    return JSONResponse({"ok": True})


def call_vancelian_backend(update: Dict[str, Any], chat_id: int, text: str) -> str:
    if not VANCELIAN_BACKEND_URL:
        return f"✅ Reçu: {text}"

    url = f"{VANCELIAN_BACKEND_URL}/internal/ganopa/telegram"

    headers = {"Content-Type": "application/json"}
    if VANCELIAN_INTERNAL_TOKEN:
        headers["X-Internal-Token"] = VANCELIAN_INTERNAL_TOKEN

    payload = {
        "update_id": update.get("update_id"),
        "chat_id": chat_id,
        "text": text,
        "raw": update,
    }

    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            return (data.get("reply_text") or "").strip() or "✅ OK"
    except Exception as e:
        logger.exception("vancelian_backend_call_failed", extra={"err": str(e)})
        return "⚠️ Backend Vancelian indisponible."


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

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return

    logger.info("telegram_message", extra={"chat_id": chat_id, "text": text[:120]})

    reply = call_vancelian_backend(update, chat_id, text)
    send_telegram_message(chat_id, reply)


def send_telegram_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload)
            # utile pour debug prod
            if resp.status_code >= 400:
                logger.error(
                    "telegram_send_failed_http",
                    extra={"chat_id": chat_id, "status": resp.status_code, "body": resp.text[:300]},
                )
            resp.raise_for_status()
    except Exception as e:
        logger.exception("telegram_send_failed", extra={"chat_id": chat_id, "err": str(e)})
