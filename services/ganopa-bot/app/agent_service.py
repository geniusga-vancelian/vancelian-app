"""
Agent service for CTO Agent.

Builds messages for OpenAI with documentation context and memory.
"""

import logging
import time
from typing import Any, Dict, List, Tuple

import httpx

from .config import OPENAI_API_KEY, OPENAI_MODEL, MEMORY_TTL_SECONDS, MEMORY_MAX_MESSAGES
from .doc_store import load_docs
from .memory_store import MemoryStore

logger = logging.getLogger("ganopa-bot")

# Global memory store instance (will be initialized with config values)
_memory_store = None


def _get_memory_store() -> MemoryStore:
    """Get or create memory store instance."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore(ttl_seconds=MEMORY_TTL_SECONDS, max_messages=MEMORY_MAX_MESSAGES)
    return _memory_store


def build_messages(
    chat_id: int,
    user_text: str,
    docs_dir: str,
    docs_refresh_seconds: int = 300,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """
    Build messages for OpenAI API with documentation context and memory.
    
    Args:
        chat_id: Telegram chat ID
        user_text: User message text
        docs_dir: Path to docs directory
        docs_refresh_seconds: TTL for docs cache refresh
        
    Returns:
        Tuple of (messages, meta)
        - messages: List of messages in OpenAI format [{role, content}, ...]
        - meta: Metadata dict with docs_hash, fresh_context, etc.
    """
    # Check memory
    memory_store = _get_memory_store()
    memory = memory_store.get(chat_id)
    fresh_context = memory is None
    
    # Always load docs (they are cached, so it's cheap)
    # This ensures the doc is always available in the system prompt
    docs_text, docs_hash = load_docs(docs_dir, refresh_seconds=docs_refresh_seconds)
    
    if fresh_context:
        logger.info(
            "memory_miss",
            extra={
                "chat_id": chat_id,
                "docs_dir": docs_dir,
                "docs_hash": docs_hash,
                "docs_length": len(docs_text),
                "docs_loaded": bool(docs_text),
            },
        )
    else:
        logger.info(
            "memory_hit",
            extra={
                "chat_id": chat_id,
                "message_count": len(memory),
                "docs_hash": docs_hash,
                "docs_loaded": bool(docs_text),
            },
        )
    
    # Build system prompt
    system_prompt_parts = [
        "You are Ganopa, a CTO assistant specialized in fintech.",
        "You help with technical decisions, architecture, and operations.",
        "Reply in French unless the user writes in another language.",
        "Be concise and helpful. Keep responses under 200 words.",
    ]
    
    # Always add documentation context if available (even if memory exists)
    # This ensures the bot always has access to the documentation
    if docs_text:
        system_prompt_parts.append(
            "\n\n=== DOCUMENTATION (SOURCE OF TRUTH) ===\n"
            "Use the documentation below as source of truth. Always refer to it when answering questions.\n"
            "If the user asks about architecture, deployment, decisions, or technical details, use this documentation.\n\n"
            f"{docs_text}\n"
            "=== END DOCUMENTATION ===\n"
        )
        logger.info(
            "docs_injected",
            extra={
                "chat_id": chat_id,
                "docs_hash": docs_hash,
                "docs_length": len(docs_text),
                "system_prompt_length": len("\n".join(system_prompt_parts)),
            },
        )
    else:
        logger.warning(
            "docs_not_loaded",
            extra={
                "chat_id": chat_id,
                "docs_dir": docs_dir,
                "docs_hash": docs_hash,
            },
        )
    
    system_prompt = "\n".join(system_prompt_parts)
    
    # Build messages list
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add memory (conversation history)
    if memory:
        messages.extend(memory)
    
    # Add current user message
    messages.append({"role": "user", "content": user_text})
    
    # Build metadata
    meta = {
        "docs_hash": docs_hash,
        "fresh_context": fresh_context,
        "memory_messages": len(memory) if memory else 0,
        "docs_included": bool(docs_text),
    }
    
    return messages, meta


def call_openai(messages: List[Dict[str, str]]) -> str:
    """
    Call OpenAI API with messages.
    
    Args:
        messages: List of messages in OpenAI format
        
    Returns:
        AI-generated response or fallback message on error
    """
    # Check API key
    if not OPENAI_API_KEY:
        logger.error(
            "openai_error",
            extra={"error": "missing_api_key"},
        )
        return "⚠️ OPENAI_API_KEY manquante (backend config)."
    
    # Log before OpenAI call
    start_time = time.time()
    logger.info(
        "openai_called",
        extra={
            "model": OPENAI_MODEL,
            "messages_count": len(messages),
            "system_prompt_length": len(messages[0]["content"]) if messages else 0,
        },
    )
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 300,
    }
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code >= 400:
                error_body = response.text[:500]
                logger.error(
                    "openai_error",
                    extra={
                        "status_code": response.status_code,
                        "error_body": error_body,
                        "latency_ms": latency_ms,
                        "error_type": "http_error",
                    },
                )
                
                if response.status_code == 401:
                    return "⚠️ Erreur d'authentification API. Veuillez contacter le support."
                elif response.status_code == 429:
                    return "⚠️ Trop de requêtes. Veuillez réessayer dans quelques instants."
                elif response.status_code >= 500:
                    return "⚠️ Service temporairement indisponible. Veuillez réessayer plus tard."
                else:
                    return "⚠️ Erreur lors du traitement de votre demande. Veuillez réessayer."
            
            data = response.json()
            
            choices = data.get("choices", [])
            if not choices:
                logger.warning(
                    "openai_error",
                    extra={"error": "empty_choices"},
                )
                return "⚠️ Réponse vide de l'API. Veuillez reformuler votre question."
            
            content = (
                choices[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            
            if not content:
                logger.warning(
                    "openai_error",
                    extra={"error": "empty_content"},
                )
                return "⚠️ Je n'ai pas pu générer de réponse. Pouvez-vous reformuler votre question ?"
            
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            response_len = len(content)
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "openai_ok",
                extra={
                    "model": OPENAI_MODEL,
                    "response_len": response_len,
                    "tokens_used": tokens_used,
                    "latency_ms": latency_ms,
                    "http_status": response.status_code,
                },
            )
            
            return content
            
    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "openai_error",
            extra={
                "error": "timeout",
                "error_type": "timeout",
                "latency_ms": latency_ms,
            },
        )
        return "⚠️ Délai d'attente dépassé. Veuillez réessayer."
        
    except httpx.NetworkError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "openai_error",
            extra={
                "error": "network_error",
                "error_type": "network_error",
                "error_detail": str(e)[:200],
                "latency_ms": latency_ms,
            },
        )
        return "⚠️ Problème de connexion. Veuillez réessayer dans quelques instants."
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.exception(
            "openai_error",
            extra={
                "error": "unexpected_error",
                "error_type": type(e).__name__,
                "error_detail": str(e)[:200],
                "latency_ms": latency_ms,
            },
        )
        return "⚠️ Erreur inattendue. Veuillez réessayer ou contacter le support."


def format_reply(raw_reply: str, meta: Dict[str, Any]) -> str:
    """
    Format reply with prefix if fresh context and doc status indicator.
    
    Args:
        raw_reply: Raw reply from OpenAI
        meta: Metadata from build_messages
        
    Returns:
        Formatted reply with prefix if needed
    """
    fresh_context = meta.get("fresh_context", False)
    docs_hash = meta.get("docs_hash", "unknown")
    docs_included = meta.get("docs_included", False)
    
    # Log for debugging
    logger.info(
        "format_reply",
        extra={
            "fresh_context": fresh_context,
            "docs_hash": docs_hash,
            "docs_included": docs_included,
        },
    )
    
    # Always add doc status prefix if doc is loaded
    # This provides visual confirmation that the doc is being used
    doc_prefix = ""
    if docs_hash != "no-docs" and docs_included:
        doc_prefix = "(doc ok) "
    elif docs_hash == "no-docs":
        doc_prefix = "(doc non disponible) "
    
    # Log the prefix being added
    logger.info(
        "format_reply_prefix",
        extra={
            "doc_prefix": doc_prefix,
            "docs_hash": docs_hash,
            "docs_included": docs_included,
            "fresh_context": fresh_context,
        },
    )
    
    # Add fresh context message if first message
    if fresh_context:
        if docs_hash != "no-docs" and docs_included:
            prefix = f"{doc_prefix}J'ai bien relu toute la doc (version: {docs_hash}), je suis prêt à répondre.\n\n"
        else:
            # Doc not loaded, but fresh context - still add prefix but mention it
            prefix = f"{doc_prefix}Je suis prêt à répondre (doc non disponible: {docs_hash}).\n\n"
        return prefix + raw_reply
    
    # For subsequent messages, ALWAYS add doc status prefix
    # This ensures (doc ok) appears on every message
    if doc_prefix:
        final_reply = doc_prefix + raw_reply
        logger.info(
            "format_reply_applied",
            extra={
                "doc_prefix": doc_prefix,
                "reply_length": len(final_reply),
                "reply_preview": final_reply[:100],
            },
        )
        return final_reply
    
    # Fallback: if no prefix, return raw reply (should not happen)
    logger.warning(
        "format_reply_no_prefix",
        extra={
            "docs_hash": docs_hash,
            "docs_included": docs_included,
        },
    )
    return raw_reply

