import os
import httpx

GITHUB_API = "https://api.github.com"

class GitHubClient:
    def __init__(self):
        self.owner = os.environ["GITHUB_OWNER"]
        self.repo = os.environ["GITHUB_REPO"]
        self.token = os.environ["GITHUB_TOKEN"]  # PAT avec scope repo + workflow
        self.base_headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @property
    def repo_full(self) -> str:
        return f"{self.owner}/{self.repo}"

    def create_issue(self, title: str, body: str, labels=None) -> dict:
        labels = labels or []
        url = f"{GITHUB_API}/repos/{self.repo_full}/issues"
        payload = {"title": title, "body": body, "labels": labels}
        with httpx.Client(timeout=30) as c:
            r = c.post(url, headers=self.base_headers, json=payload)
            r.raise_for_status()
            return r.json()

    def comment_issue(self, issue_number: int, body: str) -> dict:
        url = f"{GITHUB_API}/repos/{self.repo_full}/issues/{issue_number}/comments"
        with httpx.Client(timeout=30) as c:
            r = c.post(url, headers=self.base_headers, json={"body": body})
            r.raise_for_status()
            return r.json()

    def dispatch_workflow(self, workflow_file: str, ref: str, inputs: dict) -> None:
        # workflow_file = "agent.yml" or "ops.yml"
        url = f"{GITHUB_API}/repos/{self.repo_full}/actions/workflows/{workflow_file}/dispatches"
        payload = {"ref": ref, "inputs": inputs}
        with httpx.Client(timeout=30) as c:
            r = c.post(url, headers=self.base_headers, json=payload)
            r.raise_for_status()
