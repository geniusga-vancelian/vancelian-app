# scripts/aws/github-oidc

Bootstrap & inventory tooling for the GitHub Actions ↔ AWS OIDC integration
that powers the `arquantix-*-deploy.yml` workflows.

> Read the **full operational guide** at [`docs/arquantix/CI_AWS_OIDC_SETUP.md`](../../../docs/arquantix/CI_AWS_OIDC_SETUP.md).

## Files

| File | Purpose |
|------|---------|
| `setup.sh` | Idempotently provisions the OIDC provider + the `arquantix-github-actions-deployer` IAM role with a scoped inline policy. Re-runnable anytime. |
| `inventory.sh` | Read-only check of expected AWS resources (ECR repos, ECS cluster + services, IAM roles, OIDC provider). Useful after any infra change. |
| `trust-policy.json.template` | Trust policy template (placeholders are substituted by `setup.sh`). |
| `permissions-policy.json.template` | Inline policy template scoped to `arquantix-*` ECR repos and the `arquantix-cluster`. |

## Quickstart

```bash
# Phase A: get a temporary admin access key (AWS Console, see docs)
aws configure                              # paste keys, region me-central-1

# Phase B: bootstrap (idempotent)
./scripts/aws/github-oidc/setup.sh

# Phase C: copy the printed Role ARN into GitHub repo secret AWS_ROLE_ARN
# Phase D: verify
./scripts/aws/github-oidc/inventory.sh
```

## Required AWS permissions to run `setup.sh`

`setup.sh` needs admin-equivalent IAM rights, but **only once**, to:

- `iam:CreateOpenIDConnectProvider` (one shared resource per AWS account, idempotent)
- `iam:CreateRole`, `iam:GetRole`, `iam:UpdateAssumeRolePolicy`
- `iam:PutRolePolicy`

After that, **revoke the bootstrap access key**. The GitHub workflows will get
short-lived (max 1h) STS credentials via OIDC, no static keys to rotate.

## Customizing the scope

Want to allow only the `main` branch (instead of all branches)? Edit
`trust-policy.json.template`:

```diff
-          "token.actions.githubusercontent.com:sub": "repo:__GITHUB_OWNER__/__GITHUB_REPO__:*"
+          "token.actions.githubusercontent.com:sub": "repo:__GITHUB_OWNER__/__GITHUB_REPO__:ref:refs/heads/main"
```

Then re-run `setup.sh` — it updates the trust policy in place.

Want to grant more AWS permissions (S3, CloudFront, etc.)? Edit
`permissions-policy.json.template` and re-run `setup.sh` (it does
`put-role-policy` which replaces the inline policy).
