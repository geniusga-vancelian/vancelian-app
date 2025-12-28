from os import getenv
from dotenv import load_dotenv

# 🔑 Charge automatiquement le fichier .env
load_dotenv()


def getenv_required(name: str) -> str:
    value = getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


TELEGRAM_BOT_TOKEN = getenv_required("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = getenv_required("WEBHOOK_SECRET")
