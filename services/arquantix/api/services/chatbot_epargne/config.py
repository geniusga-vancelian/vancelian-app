"""
Minimal config for Bot IA épargne: OpenAI env vars.
Use OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL from environment.
"""
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
