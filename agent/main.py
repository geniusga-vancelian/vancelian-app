import os
import sys

def main():
    # Plus tard on branchera OpenAI + tes outils (git diff, tests, etc.)
    env = os.getenv("TARGET_ENV", "dev")
    action = os.getenv("ACTION", "PLAN")
    prompt = os.getenv("PROMPT", "")

    print("=== Vancelian Agent ===")
    print(f"env={env}")
    print(f"action={action}")
    print(f"prompt={prompt[:200]}")

    # placeholder
    if action == "PLAN":
        print("TODO: generate a product/dev plan")
    elif action == "QA":
        print("TODO: run QA checks (pytest/ruff) and summarize")
    else:
        print("Unknown action:", action)
        sys.exit(2)

if __name__ == "__main__":
    main()
