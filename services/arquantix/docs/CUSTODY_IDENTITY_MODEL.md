# Modèle d’identité — Custody CMS → API (Option B)

## Rôles

| Rôle | Description |
|------|-------------|
| **Titulaire métier** | Le client (`person_id` / `pe_client`) pour lequel on crée ou gère un compte custody. |
| **Opérateur CMS** | Utilisateur connecté au back-office Next (`users` Prisma) — authentifié par session cookie. |
| **Principal technique JWT** | Identité `admin_users.id` utilisée dans le claim `sub` = `au:<id>` — **compte de service** partagé (`BFF_ANONYMOUS_BACKEND_ADMIN_ID`), pas l’opérateur humain. |

## Flux BFF

1. Vérifier session CMS + rôle `ADMIN` ou `SUPER_ADMIN`.
2. Mint JWT avec `signInternalBackendJwtAu(BFF_ANONYMOUS_BACKEND_ADMIN_ID)`.
3. Transmettre vers l’API Python :
   - `Authorization: Bearer <JWT>`
   - `X-Actor-Type: service`, `X-Actor-Id: <CMS_CUSTODY_SERVICE_ACTOR_ID|cms-custody-service>`
   - `X-CMS-User-Id`, `X-CMS-User-Email`, `X-CMS-User-Roles`
   - `X-Request-Id` (UUID)

## Audit API

Les événements sensibles custody enrichissent les métadonnées avec les champs CMS (voir `services/custody/cms_operator_audit.py`).
