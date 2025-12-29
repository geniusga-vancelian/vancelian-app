"""
Documentation store for CTO Agent.

Loads and caches documentation from /docs directory.
Calculates hash for version tracking.
"""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("ganopa-bot")

# Global cache for docs
_docs_cache: dict[str, Tuple[str, str, float]] = {}  # {docs_dir: (docs_text, docs_hash, timestamp)}


def load_docs(docs_dir: str, refresh_seconds: int = 300) -> Tuple[str, str]:
    """
    Load all .md files from docs directory and return concatenated text + hash.
    
    Args:
        docs_dir: Path to docs directory
        refresh_seconds: TTL for cache refresh (default: 300 = 5 minutes)
        
    Returns:
        Tuple of (docs_text, docs_hash)
        - docs_text: Concatenated content of all .md files
        - docs_hash: SHA256 hash (first 12 characters)
        - If docs directory doesn't exist or is empty, returns ("", "no-docs")
    """
    current_time = time.time()
    
    # Check cache
    if docs_dir in _docs_cache:
        cached_text, cached_hash, cached_time = _docs_cache[docs_dir]
        if current_time - cached_time < refresh_seconds:
            logger.debug(
                "docs_cache_hit",
                extra={"docs_dir": docs_dir, "hash": cached_hash},
            )
            return cached_text, cached_hash
    
    # Load docs from filesystem
    docs_path = Path(docs_dir)
    
    if not docs_path.exists() or not docs_path.is_dir():
        logger.warning(
            "docs_dir_not_found",
            extra={"docs_dir": docs_dir},
        )
        _docs_cache[docs_dir] = ("", "no-docs", current_time)
        return "", "no-docs"
    
    # Find all .md files and sort for stable order
    md_files = sorted(docs_path.glob("*.md"))
    
    if not md_files:
        logger.warning(
            "docs_dir_empty",
            extra={"docs_dir": docs_dir},
        )
        _docs_cache[docs_dir] = ("", "no-docs", current_time)
        return "", "no-docs"
    
    # Read and concatenate all .md files
    docs_parts = []
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            docs_parts.append(f"# {md_file.name}\n\n{content}\n\n")
        except Exception as e:
            logger.error(
                "docs_file_read_error",
                extra={"file": str(md_file), "error": str(e)},
            )
            continue
    
    if not docs_parts:
        logger.warning(
            "docs_no_readable_files",
            extra={"docs_dir": docs_dir},
        )
        _docs_cache[docs_dir] = ("", "no-docs", current_time)
        return "", "no-docs"
    
    # Concatenate with separators
    docs_text = "\n---\n\n".join(docs_parts)
    
    # Calculate hash (SHA256, first 12 characters)
    docs_hash = hashlib.sha256(docs_text.encode("utf-8")).hexdigest()[:12]
    
    # Truncate if too long (60k chars max for OpenAI context)
    max_length = 60000
    if len(docs_text) > max_length:
        logger.warning(
            "docs_truncated",
            extra={
                "docs_dir": docs_dir,
                "original_length": len(docs_text),
                "truncated_length": max_length,
            },
        )
        docs_text = docs_text[:max_length] + "\n\n[... documentation tronquée ...]"
        # Recalculate hash after truncation
        docs_hash = hashlib.sha256(docs_text.encode("utf-8")).hexdigest()[:12]
    
    # Update cache
    _docs_cache[docs_dir] = (docs_text, docs_hash, current_time)
    
    logger.info(
        "docs_loaded",
        extra={
            "docs_dir": docs_dir,
            "hash": docs_hash,
            "length": len(docs_text),
            "files_count": len(md_files),
        },
    )
    
    return docs_text, docs_hash

