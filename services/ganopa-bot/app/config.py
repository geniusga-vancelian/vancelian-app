"""
Configuration management for Ganopa bot.

Loads environment variables required for operation.
In production (ECS), env vars are injected by the task definition.
No .env file loading in production - only use environment variables.
"""

from os import getenv


def getenv_required(name: str) -> str:
    """
    Get required environment variable.
    
    Raises RuntimeError if variable is missing or empty.
    """
    value = (getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def getenv_bool(name: str, default: bool = False) -> bool:
    """
    Get boolean environment variable.
    
    Returns True if value is "1", "true", "yes" (case insensitive).
    Returns False otherwise or if not set.
    """
    value = (getenv(name) or "").strip().lower()
    return value in ("1", "true", "yes", "on")


# -------------------------------------------------
# Service Configuration
# -------------------------------------------------

SERVICE_NAME = "ganopa-bot"

# Build ID from environment (default: "dev")
# Set BUILD_ID in ECS task definition to identify deployed version
BUILD_ID = (getenv("BUILD_ID") or "dev").strip()

# Port (default: "8000")
# Set PORT in ECS task definition if different
PORT = (getenv("PORT") or "8000").strip()


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

# OpenAI API key (optional - will log has_openai_key boolean)
# If not set, bot will return error message to user
OPENAI_API_KEY = (getenv("OPENAI_API_KEY") or "").strip()

# OpenAI model to use (default: gpt-4o-mini)
OPENAI_MODEL = (getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()


# -------------------------------------------------
# Bot Configuration
# -------------------------------------------------

# Signature test mode: if enabled, bot responds with version test message
# Set BOT_SIGNATURE_TEST=1 to enable
BOT_SIGNATURE_TEST = getenv_bool("BOT_SIGNATURE_TEST", default=False)
