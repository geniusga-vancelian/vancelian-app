# Vancelian Agent 🤖

The **Vancelian Agent** is an AI-powered orchestration layer designed to act as a
**virtual product, engineering, DevOps, and QA team** for the Vancelian platform.

Its purpose is to translate **high-level intent** (product ideas, fixes, audits,
deployments) into **structured, actionable plans** and, progressively,
into **automated execution**.

This agent is intentionally designed to reduce human operational load and avoid
manual DevOps work as much as possible.

---

## 🎯 Vision

The agent will progressively become capable of:

- Acting as a **Product Manager**
  - Clarifying requirements
  - Breaking down features into tasks
  - Identifying risks and dependencies

- Acting as a **Software Engineer**
  - Proposing backend / frontend architecture
  - Generating implementation plans
  - Reviewing code and diffs

- Acting as **DevOps**
  - Planning infrastructure changes
  - Validating CI/CD pipelines
  - Deploying safely across environments (dev / staging / prod)

- Acting as **QA**
  - Identifying edge cases
  - Proposing test scenarios
  - Detecting regressions

Ultimately, the goal is for the agent to become a **self-operating digital team**
that can manage most of the technical lifecycle of Vancelian.

---

## 🧠 Core Concepts

The agent is driven by **intent**, not low-level commands.

Each run is defined by:

- `TARGET_ENV` — the environment concerned (`dev`, `staging`, `prod`)
- `ACTION` — what the agent is expected to do
- `PROMPT` — a human-readable instruction

Example intents:
- "Plan a deposits flow"
- "Audit production infrastructure"
- "Prepare a safe production deployment"
- "Analyze why a deployment failed"

---

## 📂 Project Structure

```text
agent/
├── main.py            # Agent entrypoint
├── requirements.txt   # Python dependencies
└── README.md          # This documentation
