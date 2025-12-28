from fastapi import FastAPI

from .telegram_router import router as telegram_router

# -------------------------------------------------
# App
# -------------------------------------------------

app = FastAPI(title="Ganopa Agent Bot")

# -------------------------------------------------
# Routes de base
# -------------------------------------------------

@app.get("/")
def root():
    return {"ok": True, "service": "ganopa-bot"}

@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------------------------------
# Telegram webhook routes
# -------------------------------------------------

app.include_router(telegram_router)
