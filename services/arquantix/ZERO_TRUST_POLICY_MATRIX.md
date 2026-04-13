# Matrice de politique Zero Trust (référence)

Les valeurs numériques proviennent de `ACTION_POLICY_MAP` et des variables d’environnement (`ZERO_TRUST_DENY_ALL_RISK_THRESHOLD`, `ZERO_TRUST_STEP_UP_RISK_THRESHOLD`, `ZERO_TRUST_STRICT_DEFAULT_ACCESS`). Le **risque effectif** = max(`global_risk_score`, `fraud_score × 100` arrondi).

| Action | Ressource (exemple) | Auth minimale | Refus si risque effectif ≥ | Step-up si risque ≥ seuil action | Rôles exclus (RBAC) |
|--------|---------------------|---------------|----------------------------|-----------------------------------|---------------------|
| `session.api_access` | `*` | `password` | 95 (global) | 70 (informatif si non strict) | — |
| `auth.refresh` | `*` | `password` | 95 | 70 | — |
| `auth.revoke_all` | `user:{id}` | `otp` | 90 (sensible) | 70 | `support`, `readonly`, `user` |
| `kyc.read` | `person:{uuid}` | `password` | 90 | 70 | — |
| `kyc.write` | `person:{uuid}` | `otp` | 90 | 70 | `readonly`, `user` |
| `custody.withdraw` | TBD | `passkey` | 90 | 70 | `support`, `readonly`, `user` |
| `custody.transfer` | TBD | `passkey` | 90 | 70 | `support`, `readonly`, `user` |
| `security.admin` | `*` | `otp` | 90 | 70 | `support`, `readonly`, `user` |
| `crypto.sensitive_decrypt` | `contact:{id}` / `data:*` | `otp` | 85 | 65 | selon route |
| `admin.list_admins` | `admin_users` | `otp` | 90 | 70 | — |

### Règles transverses

- Compte verrouillé ou device bloqué (réputation / trust `BLOCKED`) → **deny** immédiat.
- Device **SUSPICIOUS** + action sensible + auth &lt; `otp` → **restrict** / step-up.
- Ordre de force : `password` &lt; `otp` &lt; `passkey` &lt; `passkey+attestation`.

### Évolution

- Remplacer ce tableau par une source unique (DB/YAML) synchronisée avec `POST /admin/security/policies/reload` une fois le chargeur implémenté.
