"""
Telegram update handlers and command routing for Ganopa bot.

Handles parsing of Telegram updates, command routing, and response generation.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from .config import SERVICE_NAME, BUILD_ID, OPENAI_MODEL

# Import VERSION from main (set at runtime)
VERSION = "ganopa-bot-dev"  # Default, will be overridden by main.py

logger = logging.getLogger("ganopa-bot")

# Maximum message length for Telegram (4096 chars, we use 3500 for safety)
MAX_MESSAGE_LENGTH = 3500


def parse_update(update: Dict[str, Any]) -> Tuple[Optional[int], Optional[str], Optional[int], bool, Optional[int], Optional[int]]:
    """
    Parse a Telegram update and extract key information.
    
    Args:
        update: Telegram update dictionary
        
    Returns:
        Tuple of (chat_id, text, user_id, is_bot, message_id, update_id)
        Returns None for missing values.
    """
    update_id = update.get("update_id")
    
    # Get message (from update or edited_message)
    message = update.get("message") or update.get("edited_message")
    if not message:
        return None, None, None, False, None, update_id
    
    # Extract message info
    message_id = message.get("message_id")
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    
    # Extract user info
    from_user = message.get("from", {})
    user_id = from_user.get("id")
    is_bot = from_user.get("is_bot", False)
    
    return chat_id, text, user_id, is_bot, message_id, update_id


def route_command(
    text: str,
    *,
    correlation_id: str,
    chat_id: Optional[int] = None,
    update_id: Optional[int] = None,
) -> Optional[str]:
    """
    Route Telegram commands to appropriate handlers.
    
    Args:
        text: Message text from user
        correlation_id: Correlation ID for logging
        chat_id: Telegram chat ID
        update_id: Telegram update ID
        
    Returns:
        Response text or None if not a command
    """
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # /start command
    if text_lower == "/start":
        logger.info(
            "command_start",
            extra={
                "correlation_id": correlation_id,
                "chat_id": chat_id,
                "update_id": update_id,
            },
        )
        return (
            f"👋 Bienvenue sur Ganopa !\n\n"
            f"Je suis votre assistant IA spécialisé en fintech.\n\n"
            f"📋 Commandes disponibles:\n"
            f"• /help - Afficher l'aide\n"
            f"• /status - État du service\n\n"
            f"💬 Posez-moi une question et je vous répondrai avec l'IA.\n\n"
            f"🔧 Version: {VERSION}"
        )
    
    # /help command
    if text_lower == "/help":
        logger.info(
            "command_help",
            extra={
                "correlation_id": correlation_id,
                "chat_id": chat_id,
                "update_id": update_id,
            },
        )
        return (
            f"📚 Aide - Ganopa Bot\n\n"
            f"Commandes:\n"
            f"• /start - Message d'accueil\n"
            f"• /help - Afficher cette aide\n"
            f"• /status - État du service et version\n\n"
            f"Usage:\n"
            f"Envoyez-moi un message et je vous répondrai avec l'IA.\n"
            f"Je peux vous aider sur des questions liées à la fintech, "
            f"les paiements, la banque, etc.\n\n"
            f"Exemple: \"Explique-moi les paiements instantanés\""
        )
    
    # /status command
    if text_lower == "/status":
        logger.info(
            "command_status",
            extra={
                "correlation_id": correlation_id,
                "chat_id": chat_id,
                "update_id": update_id,
            },
        )
        return (
            f"📊 État du Service\n\n"
            f"✅ Service: {SERVICE_NAME}\n"
            f"🔧 Version: {VERSION}\n"
            f"🏷️  Build ID: {BUILD_ID}\n"
            f"🤖 Modèle IA: {OPENAI_MODEL}\n"
            f"💚 Statut: Opérationnel"
        )
    
    # Not a command
    return None


def truncate_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """
    Truncate a message to fit Telegram's length limit.
    
    Args:
        text: Message text to truncate
        max_length: Maximum length (default: 3500)
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    
    # Truncate and add ellipsis
    truncated = text[:max_length - 3] + "..."
    logger.warning(
        "message_truncated",
        extra={
            "original_length": len(text),
            "truncated_length": len(truncated),
        },
    )
    return truncated

