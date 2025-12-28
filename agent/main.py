import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
import re
try:
    import yaml
except Exception:
    yaml = None



def load_product_vision() -> dict:
    if yaml is None:
        return {}
    path = Path("product/vision.yaml")
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def render_product_context(vision: dict) -> str:
    p = (vision or {}).get("product", {})
    modules = (p.get("modules") or {})

    name = p.get("name", "Vancelian")
    domain = p.get("domain", "")
    principles = p.get("principles", [])
    envs = p.get("environments", [])

    lines = []
    lines.append("## Product context (from product/vision.yaml)")
    lines.append(f"- name: **{name}**")
    if domain:
        lines.append(f"- domain: **{domain}**")
    if envs:
        lines.append(f"- environments: {', '.join(envs)}")
    if principles:
        lines.append("- principles:")
        for x in principles:
            lines.append(f"  - {x}")

    if modules:
        lines.append("- modules:")
        for k, v in modules.items():
            if isinstance(v, dict):
                status = v.get("status", "unknown")
                extra = []
                for kk in ["currency", "yield"]:
                    if kk in v:
                        extra.append(f"{kk}={v[kk]}")
                suffix = f" ({', '.join(extra)})" if extra else ""
                lines.append(f"  - {k}: **{status}**{suffix}")
            else:
                lines.append(f"  - {k}: {v}")

    return "\n".join(lines) + "\n"

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def header(env: str, action: str) -> str:
    return f"# Vancelian Agent — {action}\n\n- env: **{env}**\n- generated_at: **{now_utc_iso()}**\n"


def plan_markdown(env: str, prompt: str) -> str:
    # V1: plan "product/dev" générique mais actionnable
    # (On specialisera ensuite: deposits, vaults, kyc, etc.)
    vision = load_product_vision()
    md = []
    md.append(header(env, "PLAN"))
    md.append(f"## Prompt\n{prompt}\n")
    if vision:
        md.append(render_product_context(vision))
    md.append("## 1) Scope\n- What we are building\n- What is explicitly out-of-scope\n- Assumptions / constraints\n")
    md.append("## 2) User stories\n- As a user, I can ...\n- As an admin, I can ...\n")
    md.append("## 3) API design\n- Endpoints (method + path)\n- Request/response payloads\n- Error codes\n- Idempotency strategy (if applicable)\n")
    md.append("## 4) Data model\n- Tables / collections\n- Key fields\n- State machine (status transitions)\n")
    md.append("## 5) Security & compliance checks\n- AuthZ/authN requirements\n- KYC/AML gating rules (if applicable)\n- Audit trail expectations\n")
    md.append("## 6) QA plan\n- Unit tests\n- Integration tests\n- Negative cases\n- Monitoring / alerts\n")
    md.append("## 7) Delivery plan\n- Milestone 1 (MVP)\n- Milestone 2\n- Definition of Done\n")
    md.append("\n---\n")
    md.append("### Next questions for you (to refine)\n- What’s the exact feature boundary?\n- Any must-have edge cases?\n- Any performance or compliance constraints?\n")
    return "\n".join(md)


def qa_markdown(env: str, prompt: str) -> str:
    md = []
    md.append(header(env, "QA"))
    if prompt.strip():
        md.append(f"## Context\n{prompt}\n")
    md.append("## Checklist\n- [ ] App boots / endpoints reachable\n- [ ] Lint / formatting\n- [ ] Unit tests pass\n- [ ] Integration tests pass\n- [ ] AuthZ checks validated\n- [ ] Error handling validated (4xx/5xx)\n- [ ] Logging & correlation IDs present\n- [ ] Observability hooks (metrics/alerts) defined\n")
    md.append("## Negative tests\n- [ ] Invalid payloads\n- [ ] Missing auth\n- [ ] Wrong permissions\n- [ ] Idempotency collisions (if relevant)\n")
    md.append("## Release gates\n- [ ] Rollback plan exists\n- [ ] Ops workflow can restart/rollback/scale\n- [ ] Health check stable\n")
    return "\n".join(md)


def build_json(env: str, action: str, prompt: str) -> dict:
    # Option 2 "bonus" dès maintenant: JSON exploitable par CI / Notion / Jira plus tard
    base = {
        "env": env,
        "action": action,
        "prompt": prompt,
        "generated_at": now_utc_iso(),
        "version": "v1",
    }

    if action == "PLAN":
        base["deliverable"] = {
            "sections": [
                "Scope",
                "User stories",
                "API design",
                "Data model",
                "Security & compliance checks",
                "QA plan",
                "Delivery plan",
            ],
            "next_questions": [
                "What’s the exact feature boundary?",
                "Any must-have edge cases?",
                "Any performance or compliance constraints?",
            ],
        }
    elif action == "QA":
        base["deliverable"] = {
            "checklist": [
                "App boots / endpoints reachable",
                "Lint / formatting",
                "Unit tests pass",
                "Integration tests pass",
                "AuthZ checks validated",
                "Error handling validated (4xx/5xx)",
                "Logging & correlation IDs present",
                "Observability hooks defined",
            ],
            "release_gates": [
                "Rollback plan exists",
                "Ops workflow can restart/rollback/scale",
                "Health check stable",
            ],
        }

    return base

def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "plan"

def write_plan_file(md: str, prompt: str) -> str:
    # Creates: product/plans/YYYYMMDD_HHMM_<slug>.md
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    slug = slugify(prompt)[:60]
    out_dir = Path("product/plans")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ts}_{slug}.md"
    out_path.write_text(md, encoding="utf-8")
    return str(out_path)

def main() -> None:
    env = os.getenv("TARGET_ENV", "dev").strip()
    action = os.getenv("ACTION", "PLAN").strip().upper()
    prompt = (os.getenv("PROMPT", "") or "").strip()

    if action not in {"PLAN", "QA"}:
        print(f"Unknown ACTION={action}. Expected PLAN or QA.", file=sys.stderr)
        sys.exit(2)

    if action == "PLAN" and not prompt:
        print("PROMPT is required when ACTION=PLAN", file=sys.stderr)
        sys.exit(2)

    # 1) Human-friendly output
    if action == "PLAN":
        md = plan_markdown(env, prompt)
    else:
        md = qa_markdown(env, prompt)

    print(md)

    if action == "PLAN":
        out_file = write_plan_file(md, prompt)
        print(f"\nSaved plan to: {out_file}\n")
    
    # 2) Machine-friendly output (bonus Option 2)
    payload = build_json(env, action, prompt)
    print("\n\n```json")
    print(json.dumps(payload, indent=2))
    print("```")


if __name__ == "__main__":
    main()
