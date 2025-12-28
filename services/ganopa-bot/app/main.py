from fastapi import FastAPI, Header, HTTPException, Request
import httpx

from .config import TELEGRAM_BOT_TOKEN, WEBHOOK_SECRET

app = FastAPI(title="Ganopa Agent Bot")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    # Si tu actives secret token côté Telegram, on vérifie ici
    if WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Invalid secret token")

    update = await request.json()

    # Telegram update shape
    message = (update or {}).get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return {"ok": True, "ignored": "no chat_id"}

    # Réponse simple (pour valider que le pipe marche)
    reply = f"✅ Reçu: {text}" if text else "✅ Reçu (no text)"

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply},
        )

    return {"ok": True}
