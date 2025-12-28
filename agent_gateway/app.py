import os
import re
from fastapi import FastAPI, Request, HTTPException
from agent_gateway.github_client import GitHubClient
from agent_gateway.telegram import TelegramClient

app = FastAPI()
gh = GitHubClient()
tg = TelegramClient()

REF = os.getenv("GITHUB_REF", "main")  # branche cible pour les dispatch
ISSUE_LABEL = os.getenv("BRAINSTORM_LABEL", "brainstorm")

def parse_command(text: str):
    text = (text or "").strip()
    if not text:
        return ("help", "")

    if text.startswith("/brainstorm"):
        return ("brainstorm", text.replace("/brainstorm", "", 1).strip())
    if text.startswith("/save"):
        return ("save", text.replace("/save", "", 1).strip())
    if text.startswith("/spec"):
        return ("spec", text.replace("/spec", "", 1).strip())
    if text.startswith("/tech"):
        return ("tech", text.replace("/tech", "", 1).strip())
    if text.startswith("/implement"):
        return ("implement", text.replace("/implement", "", 1).strip())
    if text.startswith("/plan"):
        return ("plan", text.replace("/plan", "", 1).strip())
    if text.startswith("/qa"):
        return ("qa", text.replace("/qa", "", 1).strip())
    if text.startswith("/deploy"):
        return ("deploy", text.replace("/deploy", "", 1).strip())
    if text.startswith("/ops"):
        return ("ops", text.replace("/ops", "", 1).strip())

    return ("help", text)

def extract_env(arg: str, default="staging"):
    arg = (arg or "").strip().lower()
    if arg in {"dev", "staging", "prod"}:
        return arg
    return default

@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-gateway"}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    body = await request.json()
    msg = body.get("message") or body.get("edited_message") or {}
    text = msg.get("text") or ""
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")

    if not chat_id:
        raise HTTPException(status_code=400, detail="Missing chat_id")

    cmd, arg = parse_command(text)

    # HELP
    if cmd == "help":
        tg.send_message(chat_id, "Commands: /brainstorm <topic> | /plan <prompt> | /qa <context> | /ops <status|restart|rollback|scale> | /deploy <dev|staging|prod>")
        return {"ok": True}

    # BRAINSTORM => crée une issue GitHub et te répond avec le lien
    if cmd == "brainstorm":
        topic = arg or "New topic"
        issue = gh.create_issue(
            title=f"[Brainstorm] {topic}",
            body="Reply in Telegram to continue. I will save key decisions here.",
            labels=[ISSUE_LABEL],
        )
        tg.send_message(chat_id, f"Brainstorm created: {issue['html_url']}\nNow tell me: goals, constraints, success metric.")
        return {"ok": True}

    # PLAN => dispatch workflow agent.yml en mode PLAN
    if cmd == "plan":
        prompt = arg
        if not prompt:
            tg.send_message(chat_id, "Usage: /plan <what to plan>")
            return {"ok": True}
        gh.dispatch_workflow(
            workflow_file="agent.yml",
            ref=REF,
            inputs={"target_env": "staging", "action": "PLAN", "prompt": prompt},
        )
        tg.send_message(chat_id, "✅ PLAN launched in GitHub Actions (agent.yml). Check Actions tab.")
        return {"ok": True}

    # QA => dispatch workflow agent.yml en mode QA (collect AWS status + checklist)
    if cmd == "qa":
        context = arg or "Run QA checks"
        gh.dispatch_workflow(
            workflow_file="agent.yml",
            ref=REF,
            inputs={"target_env": "staging", "action": "QA", "prompt": context},
        )
        tg.send_message(chat_id, "✅ QA launched in GitHub Actions (agent.yml).")
        return {"ok": True}

    # OPS => dispatch ops.yml
    if cmd == "ops":
        # ex: "/ops status prod" ou "/ops restart staging"
        parts = (arg or "").split()
        action = (parts[0] if parts else "status").lower()
        env = extract_env(parts[1] if len(parts) > 1 else "prod", default="prod")
        inputs = {"env_name": env, "action": action, "desired_count": "1"}
        gh.dispatch_workflow("ops.yml", REF, inputs)
        tg.send_message(chat_id, f"✅ OPS {action} launched for env={env}.")
        return {"ok": True}

    # DEPLOY (placeholder) => pour plus tard (on branchera sur ton pipeline build/deploy)
    if cmd == "deploy":
        env = extract_env(arg, default="staging")
        tg.send_message(chat_id, f"Deploy requested for env={env}. (Next step: wire to build/push/deploy workflow)")
        return {"ok": True}

    tg.send_message(chat_id, "Command not recognized. Type /help")
    return {"ok": True}
