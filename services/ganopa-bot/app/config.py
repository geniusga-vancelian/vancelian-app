from os import getenv
from dotenv import load_dotenv

load_dotenv()


def getenv_required(name: str) -> str:
    value = (getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value

# -------------------------------------------------
# OpenAI
# -------------------------------------------------
OPENAI_API_KEY = getenv_required("OPENAI_API_KEY")
OPENAI_MODEL = (getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()


# -------------------------------------------------
# Telegram
# -------------------------------------------------

TELEGRAM_BOT_TOKEN = getenv_required("TELEGRAM_BOT_TOKEN")

# Optionnel : si vide => pas de vérification du header Telegram
WEBHOOK_SECRET = (getenv("WEBHOOK_SECRET") or "").strip()


# -------------------------------------------------
# Backend Vancelian (connexion bot -> backend)
# -------------------------------------------------

# Ex: https://api.vancelian.com
VANCELIAN_BACKEND_URL = (getenv("VANCELIAN_BACKEND_URL") or "").strip().rstrip("/")

# Fortement recommandé (auth interne)
VANCELIAN_INTERNAL_TOKEN = (getenv("VANCELIAN_INTERNAL_TOKEN") or "").strip()
