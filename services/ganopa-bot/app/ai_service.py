"""
OpenAI API integration for Ganopa bot.
Production-ready implementation with error handling, logging, and safety measures.
"""

import logging
from typing import Optional

import httpx

from .ai_prompt import GANOPA_SYSTEM_PROMPT
from .config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger("ganopa-bot")


def call_openai(
    text: str,
    *,
    update_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    max_tokens: int = 300,
) -> str:
    """
    Call OpenAI API to generate a response for the user's message.
    
    Args:
        text: User's message text
        update_id: Telegram update ID for logging
        chat_id: Telegram chat ID for logging
        max_tokens: Maximum tokens in response (default: 300, ~200 words)
    
    Returns:
        AI-generated response string, or error message if API call fails
    """
    # Input validation
    if not text or not text.strip():
        return "👋 Bonjour ! Comment puis-je vous aider aujourd'hui ?"
    
    text = text.strip()
    
    # Log the request
    logger.info(
        "openai_call_start",
        extra={
            "update_id": update_id,
            "chat_id": chat_id,
            "model": OPENAI_MODEL,
            "text_len": len(text),
            "text_preview": text[:100],
        },
    )
    
    # Check API key
    if not OPENAI_API_KEY:
        logger.error(
            "openai_missing_api_key",
            extra={"update_id": update_id, "chat_id": chat_id},
        )
        return "⚠️ Configuration manquante côté serveur. Veuillez contacter le support."
    
    # Prepare the API request
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": GANOPA_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,  # Lower temperature for more consistent, less creative responses
        "max_tokens": max_tokens,  # Limit response length
        "top_p": 0.9,  # Nucleus sampling for better quality
    }
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Make the API call
    try:
        with httpx.Client(timeout=30.0) as client:  # Increased timeout for reliability
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            
            # Log HTTP response
            logger.info(
                "openai_http_response",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "status_code": response.status_code,
                },
            )
            
            # Handle HTTP errors
            if response.status_code >= 400:
                error_body = response.text[:500]
                logger.error(
                    "openai_http_error",
                    extra={
                        "update_id": update_id,
                        "chat_id": chat_id,
                        "status_code": response.status_code,
                        "error_body": error_body,
                    },
                )
                
                # User-friendly error messages
                if response.status_code == 401:
                    return "⚠️ Erreur d'authentification API. Veuillez contacter le support."
                elif response.status_code == 429:
                    return "⚠️ Trop de requêtes. Veuillez réessayer dans quelques instants."
                elif response.status_code >= 500:
                    return "⚠️ Service temporairement indisponible. Veuillez réessayer plus tard."
                else:
                    return "⚠️ Erreur lors du traitement de votre demande. Veuillez réessayer."
            
            # Parse successful response
            data = response.json()
            
            # Extract content safely
            choices = data.get("choices", [])
            if not choices:
                logger.warning(
                    "openai_empty_choices",
                    extra={"update_id": update_id, "chat_id": chat_id, "data": data},
                )
                return "⚠️ Réponse vide de l'API. Veuillez reformuler votre question."
            
            content = (
                choices[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            
            # Validate content
            if not content:
                logger.warning(
                    "openai_empty_content",
                    extra={"update_id": update_id, "chat_id": chat_id},
                )
                return "⚠️ Je n'ai pas pu générer de réponse. Pouvez-vous reformuler votre question ?"
            
            # Log success
            logger.info(
                "openai_call_success",
                extra={
                    "update_id": update_id,
                    "chat_id": chat_id,
                    "model": OPENAI_MODEL,
                    "response_len": len(content),
                    "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                },
            )
            
            return content
            
    except httpx.TimeoutException:
        logger.error(
            "openai_timeout",
            extra={"update_id": update_id, "chat_id": chat_id},
        )
        return "⚠️ Délai d'attente dépassé. Veuillez réessayer."
        
    except httpx.NetworkError as e:
        logger.error(
            "openai_network_error",
            extra={"update_id": update_id, "chat_id": chat_id, "error": str(e)},
        )
        return "⚠️ Problème de connexion. Veuillez réessayer dans quelques instants."
        
    except Exception as e:
        logger.exception(
            "openai_unexpected_error",
            extra={"update_id": update_id, "chat_id": chat_id, "error": str(e)},
        )
        return "⚠️ Erreur inattendue. Veuillez réessayer ou contacter le support."

