# PR C / C.1 — Mapping niveaux de résolution auth

Trois niveaux (sans modification du format JWT) :

| Niveau | Nom code | DB AdminUser | Cache `auth:user:{id}` | Usage |
|--------|-----------|--------------|------------------------|--------|
| **1** | `resolve_auth_context_jwt_only` / branche **jwt_only** de `resolve_identity_for_auth_context_fast` | Non | Optionnel miss | Claims seuls ; **aucun** `_get_current_user_internal` |
| **2** | Branche **cache** de `resolve_identity_for_auth_context_fast` | Non | Hit bundle TTL | `person_id`, `client_id`, `email` depuis le bundle |
| **3** | `resolve_auth_context_with_cache` / **db** fast / `get_current_user_strict` | Oui | Warm après lecture | Vérité serveur ; verrou / step-up / ZT sur routes strictes |

Dépendances FastAPI (PR C.1) :

| Dépendance | Comportement |
|------------|----------------|
| `get_current_user_fast` / `get_current_user_or_admin` | Ordre : bundle `auth:user:` → si miss et `person_id` dans JWT → **jwt_only** → sinon **db** |
| `get_current_user_or_admin_strict` | Toujours `_get_current_user_internal` + `Client` (comme avant PR C.1) |
| `get_current_user` / `get_current_user_strict` (`auth.py`) | Toujours **db** + `enforce_access_security` + ZT |

## Classification des chemins (résumé)

### JWT only (niveau 1)

- `resolve_auth_context_jwt_only` (appels directs futurs ou diagnostics).
- `security.deps._person_from_jwt` : si `person_id` / `pid` présents → pas de lecture `AdminUser` pour dériver la personne.

**Ne pas** utiliser JWT-only pour : refresh, revoke, custody, opérations financières, changement de sécurité, ni pour ignorer `_get_current_user_internal` quand la route exige la vérité serveur.

### JWT + cache (niveau 2 — DB user + cache identité)

- Toute route passant par `resolve_auth_context_with_cache` / `strict_db` : DB pour l’utilisateur, puis cache `person` / `client`.
- `get_current_user_or_admin` : DB stricte + `get_client_id_for_person_cached` pour `client_id`.

### Strict DB (niveau 3)

- `get_current_user` (`auth.py`) : `resolve_auth_context_strict_db`.
- `refresh` / `revoke` / `login` : logique inchangée, multiples tables.
- `resolve_person_id` (2FA) : validation `Person` en base après résolution JWT (comportement sécurité / anti-énum).

## Métriques (process-local)

- `auth_db_hits_count` — passage par `resolve_auth_context_with_cache` / chargement user en branche db du fast path.
- `auth_cache_hits_count` — hit sur entrées identité (bundle / legacy).
- `auth_jwt_only_count` — `resolve_auth_context_jwt_only` + branche jwt_only du fast path.
- `auth_resolution_mode_jwt_only` / `auth_resolution_mode_cache` / `auth_resolution_mode_db` — mode **final** de la résolution identity fast ou strict (`resolve_auth_context_with_cache` incrémente **db**).
- `db_cursor_execute_count` — optionnel si `AUTH_SQL_METRICS_ENABLED=1` (listener SQLAlchemy).

Logs DEBUG : `auth_identity_resolution` avec `auth_resolution_mode` et `route`.

Réinitialisation tests : `reset_auth_performance_metrics()`, `clear_identity_cache_for_tests()`.
