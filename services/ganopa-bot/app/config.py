"""
Configuration management for Ganopa bot.

Loads environment variables required for operation.
In production (ECS), env vars are injected by the task definition.
For local development, .env file is loaded via python-dotenv.
"""

from os import getenv

# Try to load .env for local development
# In production (ECS), this will be a no-op as .env doesn't exist
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv not installed (production)
    pass


def getenv_required(name: str) -> str:
    """
    Get required environment variable.
    
    Raises RuntimeError if variable is missing or empty.
    """
    value = (getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


# -------------------------------------------------
# Telegram Configuration
# -------------------------------------------------

TELEGRAM_BOT_TOKEN = getenv_required("TELEGRAM_BOT_TOKEN")

# Optional: Telegram webhook secret token for additional security
# If not set, webhook secret verification is disabled
WEBHOOK_SECRET = (getenv("WEBHOOK_SECRET") or "").strip()


# -------------------------------------------------
# OpenAI Configuration
# -------------------------------------------------

OPENAI_API_KEY = getenv_required("OPENAI_API_KEY")

# OpenAI model to use (default: gpt-4o-mini)
OPENAI_MODEL = (getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
