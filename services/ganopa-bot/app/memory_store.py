"""
Memory store for CTO Agent.

In-memory storage of conversation history per chat_id.
TTL-based expiration and lazy cleanup.
"""

import logging
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ganopa-bot")


class MemoryStore:
    """
    In-memory storage for conversation history.
    
    Stores messages per chat_id with TTL expiration.
    Lazy cleanup of expired entries.
    """
    
    def __init__(self, ttl_seconds: int = 1800, max_messages: int = 20):
        """
        Initialize memory store.
        
        Args:
            ttl_seconds: Time-to-live for memory entries (default: 1800 = 30 minutes)
            max_messages: Maximum number of messages per chat (default: 20)
        """
        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages
        # Format: {chat_id: {"messages": [...], "last_access": timestamp}}
        self._store: Dict[int, Dict[str, Any]] = OrderedDict()
    
    def _cleanup_expired(self) -> None:
        """Lazy cleanup of expired entries."""
        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds
        
        expired_chats = [
            chat_id
            for chat_id, data in self._store.items()
            if data["last_access"] < cutoff_time
        ]
        
        for chat_id in expired_chats:
            self._store.pop(chat_id, None)
        
        if expired_chats:
            logger.debug(
                "memory_cleanup",
                extra={"expired_count": len(expired_chats)},
            )
    
    def get(self, chat_id: int) -> Optional[List[Dict[str, str]]]:
        """
        Get conversation history for a chat_id.
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            List of messages (OpenAI format: {role, content}) or None if not found/expired
        """
        self._cleanup_expired()
        
        if chat_id not in self._store:
            return None
        
        data = self._store[chat_id]
        current_time = time.time()
        
        # Check if expired
        if current_time - data["last_access"] >= self.ttl_seconds:
            self._store.pop(chat_id, None)
            logger.debug(
                "memory_expired",
                extra={"chat_id": chat_id},
            )
            return None
        
        # Update last access time
        data["last_access"] = current_time
        # Move to end (LRU)
        self._store.move_to_end(chat_id)
        
        return data["messages"]
    
    def append(self, chat_id: int, role: str, content: str) -> None:
        """
        Append a message to conversation history.
        
        Args:
            chat_id: Telegram chat ID
            role: Message role ("user" or "assistant")
            content: Message content
        """
        self._cleanup_expired()
        
        current_time = time.time()
        
        if chat_id not in self._store:
            self._store[chat_id] = {
                "messages": [],
                "last_access": current_time,
            }
        
        data = self._store[chat_id]
        data["last_access"] = current_time
        
        # Append message
        message = {"role": role, "content": content}
        data["messages"].append(message)
        
        # Limit message count (keep most recent)
        if len(data["messages"]) > self.max_messages:
            data["messages"] = data["messages"][-self.max_messages:]
            logger.debug(
                "memory_truncated",
                extra={"chat_id": chat_id, "max_messages": self.max_messages},
            )
        
        # Move to end (LRU)
        self._store.move_to_end(chat_id)
        
        logger.debug(
            "memory_append",
            extra={
                "chat_id": chat_id,
                "role": role,
                "message_count": len(data["messages"]),
            },
        )
    
    def clear(self, chat_id: int) -> None:
        """
        Clear conversation history for a chat_id.
        
        Args:
            chat_id: Telegram chat ID
        """
        if chat_id in self._store:
            self._store.pop(chat_id, None)
            logger.debug(
                "memory_cleared",
                extra={"chat_id": chat_id},
            )
    
    def stats(self) -> Dict[str, Any]:
        """
        Get memory store statistics.
        
        Returns:
            Dictionary with stats (active_chats, total_messages, etc.)
        """
        self._cleanup_expired()
        
        total_messages = sum(len(data["messages"]) for data in self._store.values())
        
        return {
            "active_chats": len(self._store),
            "total_messages": total_messages,
            "ttl_seconds": self.ttl_seconds,
            "max_messages": self.max_messages,
        }

