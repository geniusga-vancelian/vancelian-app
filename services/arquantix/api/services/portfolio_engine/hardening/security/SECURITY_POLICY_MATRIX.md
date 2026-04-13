# Security Policy Matrix — Vancelian Portfolio Engine

## Roles

| Role     | Description                              |
|----------|------------------------------------------|
| client   | End-user, owns portfolios                |
| advisor  | Manages assigned client portfolios       |
| ops      | Operations team, broad access            |
| admin    | Full administrative access               |
| system   | Internal/automated processes             |

## Ownership Rules

| Actor    | Portfolio Access Rule                                         |
|----------|---------------------------------------------------------------|
| client   | `portfolio.client_id == actor.actor_id`                       |
| advisor  | `portfolio.client_id` in active `pe_advisor_client_assignments` |
| ops      | All                                                           |
| admin    | All                                                           |
| system   | All                                                           |

## Portfolio-Scoped Read Endpoints

| Endpoint                                          | RBAC      | Ownership |
|---------------------------------------------------|-----------|-----------|
| GET /portfolios                                   | —         | filtered  |
| GET /portfolios/{id}                              | —         | yes       |
| GET /portfolios/{id}/sleeves                      | —         | yes       |
| GET /portfolios/{id}/positions                    | —         | yes       |
| GET /portfolios/{id}/strategies                   | —         | yes       |
| GET /portfolios/{id}/target-allocations           | —         | yes       |
| GET /portfolios/{id}/rebalance-policy             | —         | yes       |
| GET /portfolios/{id}/risk-policy                  | —         | yes       |
| GET /portfolios/{id}/rebalance-preview/latest     | —         | yes       |
| GET /portfolios/{id}/valuation                    | —         | yes       |
| GET /portfolios/{id}/valuation/history            | —         | yes       |
| GET /portfolios/{id}/performance                  | —         | yes       |
| GET /portfolios/{id}/performance-series           | —         | yes       |
| GET /portfolios/{id}/benchmark                    | —         | yes       |
| GET /portfolios/{id}/drift                        | —         | yes       |
| GET /portfolios/{id}/rebalance-preview            | —         | yes       |
| GET /portfolios/{id}/orchestration-runs           | —         | yes       |
| GET /portfolios/{id}/strategy-signals             | —         | yes       |

## Portfolio-Scoped Write Endpoints

| Endpoint                                          | RBAC          | Ownership |
|---------------------------------------------------|---------------|-----------|
| POST /portfolios                                  | —             | —         |
| PATCH /portfolios/{id}                            | —             | yes       |
| POST /portfolios/{id}/sleeves                     | —             | yes       |
| POST /portfolios/{id}/orchestrate                 | ops/admin     | yes       |
| POST /portfolios/{id}/strategy-evaluation         | ops/admin     | yes       |
| POST /portfolios/{id}/valuation/snapshot           | ops/admin     | yes       |
| POST /portfolios/{id}/rebalance-plan              | —             | yes       |
| POST /rebalance-preview                           | ops/admin     | body-check|

## Transaction Endpoints (ops/admin only)

| Endpoint                                          | RBAC          |
|---------------------------------------------------|---------------|
| GET /orders                                       | ops/admin     |
| POST /orders                                      | ops/admin     |
| GET /orders/{id}                                  | ops/admin     |
| POST /orders/{id}/accept                          | ops/admin     |
| POST /orders/{id}/reject                          | ops/admin     |
| POST /orders/{id}/cancel                          | ops/admin     |
| GET /trades                                       | ops/admin     |
| POST /trades                                      | ops/admin     |
| GET /trades/{id}                                  | ops/admin     |

## Settlement Endpoints (ops/admin only)

| Endpoint                                          | RBAC          |
|---------------------------------------------------|---------------|
| GET /settlements                                  | ops/admin     |
| POST /settlements                                 | ops/admin     |
| GET /settlements/{id}                             | ops/admin     |
| POST /settlements/{id}/schedule                   | ops/admin     |
| POST /settlements/{id}/start                      | ops/admin     |
| POST /settlements/{id}/settle                     | ops/admin     |
| POST /settlements/{id}/fail                       | ops/admin     |

## Ledger Endpoints (ops/admin only)

| Endpoint                                          | RBAC          |
|---------------------------------------------------|---------------|
| GET /ledger-accounts                              | ops/admin     |
| POST /ledger-accounts                             | ops/admin     |
| GET /ledger-accounts/{id}                         | ops/admin     |
| PATCH /ledger-accounts/{id}                       | ops/admin     |
| GET /ledger-entries                               | ops/admin     |
| GET /ledger-entries/{id}                           | ops/admin     |

## Admin Endpoints (ops/admin only)

| Endpoint                                          | RBAC          |
|---------------------------------------------------|---------------|
| POST /admin/portfolios/{id}/rebuild-positions     | ops/admin     |
| POST /admin/portfolios/{id}/rebuild-valuations    | ops/admin     |
| POST /admin/portfolios/{id}/rebuild-performance   | ops/admin     |
| GET /admin/jobs                                   | ops/admin     |
| GET /admin/jobs/{id}                              | ops/admin     |
| POST /admin/.../reconcile-*                       | ops/admin     |
| GET /admin/reconciliation-reports                 | ops/admin     |
| GET /admin/reconciliation-reports/{id}            | ops/admin     |
| GET /admin/scheduled-jobs                         | ops/admin     |
| POST /admin/scheduled-jobs                        | ops/admin     |
| GET /admin/scheduled-jobs/{id}                    | ops/admin     |
| PATCH /admin/scheduled-jobs/{id}                  | ops/admin     |
| POST /admin/scheduled-jobs/run-due                | ops/admin     |
| POST /admin/scheduled-jobs/{id}/run               | ops/admin     |
| GET /admin/advisor-assignments                    | ops/admin     |
| POST /admin/advisor-assignments                   | ops/admin     |
| PATCH /admin/advisor-assignments/{id}             | ops/admin     |

## Subscription Endpoints

| Endpoint                                          | RBAC          |
|---------------------------------------------------|---------------|
| POST /subscriptions                               | —             |
| PATCH /subscriptions/{id}                         | —             |
| POST /subscriptions/{id}/provision                | ops/admin     |

## Audit Events on Security Violations

| Event                        | Triggered When                            |
|------------------------------|-------------------------------------------|
| portfolio_access_denied      | Ownership check fails on portfolio access |
| client_access_denied         | Ownership check fails on client access    |
| advisor_assignment_created   | New advisor-client assignment created      |
| advisor_assignment_updated   | Assignment status changed                 |

## List Filtering Rules

| Endpoint           | client                      | advisor                       | ops/admin/system |
|--------------------|-----------------------------|-------------------------------|------------------|
| GET /portfolios    | WHERE client_id = actor_id  | WHERE client_id IN assigned   | no filter        |

## Authentication (v1)

Headers: `X-Actor-Type`, `X-Actor-Id`, `X-Actor-Roles` (comma-separated).
Fallback: `actor_type=system`, `actor_id=None`, `roles=[]`.
Future: JWT/IdP integration replaces header extraction.
