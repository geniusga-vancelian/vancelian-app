FROM python:3.12-slim

WORKDIR /app

# 1) Install curl (pour le healthcheck ECS)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 2) Copy requirements first (for better Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copy all Python files from app/ directory
# This ensures main.py, config.py, ai_service.py, ai_prompt.py are all included
COPY services/ganopa-bot/app/ ./app/

# 4) Copy docs directory (for CTO Agent documentation context)
COPY docs/ ./docs/

# 5) Verify that critical files are present (for debugging)
RUN ls -la app/ && \
    test -f app/main.py && \
    test -f app/config.py && \
    echo "✅ All Python files are present" && \
    (test -d docs && echo "✅ Docs directory is present" || echo "⚠️  Docs directory not found (will use fallback)") || \
    (echo "❌ Missing Python files!" && exit 1)

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Utilise $PORT (ECS/Heroku-like), fallback via ENV ci-dessus
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
