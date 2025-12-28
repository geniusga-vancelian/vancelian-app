FROM python:3.12-slim

WORKDIR /app

# 1) Install curl (pour le healthcheck ECS)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Utilise $PORT (ECS/Heroku-like), fallback via ENV ci-dessus
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
