import os

def getenv_required(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v

TELEGRAM_BOT_TOKEN = getenv_required("TELEGRAM_BOT_TOKEN")
# On branchera OpenAI après
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Optionnel : simple secret pour protéger le webhook
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
