# Agent Gateway (Telegram → GitHub Actions)

The **Agent Gateway** is a lightweight FastAPI service deployed on AWS Fargate.  
It receives commands from Telegram and orchestrates GitHub Actions workflows.

The goal is to act as a **multi-role AI agent**:
- Brainstorming partner
- Product manager (plans, specs)
- Technical architect / developer
- Ops assistant (ECS / Fargate)

This service does **not** run AI itself.  
It **coordinates workflows**, artifacts, and memory stored in GitHub.

---

## Architecture overview

Telegram
|
|  (Webhook)
v
Agent Gateway (FastAPI on Fargate)
|
+–> GitHub Issues        (memory / brainstorming)
+–> agent.yml workflow  (PLAN / QA)
+–> ops.yml workflow    (ECS ops)
+–> Artifacts (.md)     (plans, specs)

---

## Supported Telegram commands

| Command | Description |
|------|------------|
| `/brainstorm <topic>` | Creates a GitHub Issue used as long-term memory |
| `/plan <prompt>` | Runs `agent.yml` in PLAN mode |
| `/qa <context>` | Runs `agent.yml` in QA mode |
| `/ops status <env>` | Checks ECS service status |
| `/ops restart <env>` | Restarts ECS service |
| `/deploy <env>` | Placeholder for deployment pipeline |
| `/help` | Shows help |

Environments: `dev`, `staging`, `prod`

---

## Environment variables

These variables must be provided to the ECS task definition:

TELEGRAM_BOT_TOKEN=xxxxxxxx
GITHUB_OWNER=geniusga-vancelian
GITHUB_REPO=vancelian-app
GITHUB_TOKEN=ghp_xxxxxxxx
GITHUB_REF=main

### Required GitHub Token scopes

The GitHub Personal Access Token must include:

- repo
- workflow

---

## Health check

Used by ALB / ECS:

GET /health

Response:
```json
{
  "status": "ok",
  "service": "agent-gateway"
}


⸻

Local development

cd agent_gateway

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN=...
export GITHUB_OWNER=geniusga-vancelian
export GITHUB_REPO=vancelian-app
export GITHUB_TOKEN=...
export GITHUB_REF=main

uvicorn agent_gateway.app:app --reload --port 8000


⸻

Docker build

docker build -t vancelian-agent-gateway .
docker run -p 8000:8000 vancelian-agent-gateway


⸻

Telegram webhook setup

Once deployed behind an HTTPS ALB:

curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -d "url=https://<ALB_DNS>/telegram/webhook"


⸻

Design principles
	•	GitHub is the source of truth
	•	No database (memory = GitHub Issues + Artifacts)
	•	Deterministic workflows (no magic)
	•	Human-in-the-loop by default
	•	Production-grade from day one (ECS, IAM, OIDC)

⸻

Roadmap
	•	Persist brainstorm decisions to Issues automatically
	•	Generate functional specs from brainstorm artifacts
	•	Generate technical specs + code skeletons
	•	Auto-open PRs with generated files
	•	Replace PAT with GitHub App
	•	Add multi-user / chat context

⸻

Status

MVP – Production-ready orchestration layer
AI logic will be plugged via workflows, not inside this service.
