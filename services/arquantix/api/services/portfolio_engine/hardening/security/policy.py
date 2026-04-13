"""Authorization policy matrix (Hardening Subphase 5).

Documents which roles may access which endpoint groups.
This module serves as living documentation and may be used for
programmatic policy checks in future phases.

Roles:
  client   — end-user / portfolio owner
  advisor  — wealth advisor managing client portfolios
  ops      — operations team
  admin    — platform administrator
  system   — internal service-to-service calls
"""

POLICY = {
    "public_reads": {
        "description": "Low-risk read endpoints (valuations, performance, drift, etc.)",
        "allowed_roles": ["client", "advisor", "ops", "admin", "system"],
        "examples": [
            "GET /portfolios/{id}/valuation/*",
            "GET /portfolios/{id}/performance*",
            "GET /portfolios/{id}/drift*",
            "GET /portfolios/{id}/benchmark",
            "GET /admin/jobs",
            "GET /admin/reconciliation-reports",
            "GET /admin/scheduled-jobs",
        ],
    },
    "sensitive_writes": {
        "description": "Operational write endpoints requiring ops or admin",
        "allowed_roles": ["ops", "admin"],
        "examples": [
            "POST /portfolios/{id}/orchestrate",
            "POST /portfolios/{id}/strategy-evaluation",
            "POST /portfolios/{id}/valuation/snapshot",
            "POST /rebalance-preview",
            "POST /subscriptions/{id}/provision",
        ],
    },
    "admin_operations": {
        "description": "Admin-only operational endpoints (rebuild, reconciliation, scheduler)",
        "allowed_roles": ["ops", "admin"],
        "examples": [
            "POST /admin/portfolios/{id}/rebuild-*",
            "POST /admin/portfolios/{id}/reconcile-*",
            "POST /admin/ledger/reconcile-balances",
            "POST /admin/scheduled-jobs",
            "POST /admin/scheduled-jobs/run-due",
            "POST /admin/scheduled-jobs/{id}/run",
            "PATCH /admin/scheduled-jobs/{id}",
        ],
    },
    "configuration": {
        "description": "Configuration management (trading fees, policies, etc.)",
        "allowed_roles": ["admin", "ops"],
        "examples": [
            "POST /trading-fees",
            "PATCH /trading-fees/{id}",
        ],
    },
}
