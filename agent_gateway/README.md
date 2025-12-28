# Agent Gateway (Telegram -> GitHub Actions)

This service receives Telegram webhooks and triggers GitHub workflows (agent.yml, ops.yml).

## Env vars
- TELEGRAM_BOT_TOKEN
- GITHUB_OWNER
- GITHUB_REPO
- GITHUB_TOKEN (PAT with repo + workflow scopes)
- GITHUB_REF (default: main)

## Local run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r agent_gateway/requirements.txt
export TELEGRAM_BOT_TOKEN=...
export GITHUB_OWNER=geniusga-vancelian
export GITHUB_REPO=vancelian-app
export GITHUB_TOKEN=...
uvicorn agent_gateway.app:app --reload --port 8000
