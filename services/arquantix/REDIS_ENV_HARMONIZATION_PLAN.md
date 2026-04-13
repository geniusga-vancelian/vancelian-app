# Harmonisation Redis auth — plan et état

## Current State

### Détection « Redis obligatoire » (avant harmonisation explicite)

- **Un seul critère effectif** : `is_auth_redis_required_env()` — désormais **routé** par `AUTH_REDIS_ENV_STRATEGY`.
- **Mode `legacy` (défaut)** : équivalent à l’historique — uniquement `ENVIRONMENT` / `ENV` ∈ `production` | `prod` | `live`. **Aucune lecture prioritaire de `APP_ENV`** pour cette décision (déploiements qui ne posent que `ENVIRONMENT`).
- **Mode `normalized`** : `get_normalized_app_env() == "production"` (chaîne prioritaire `APP_ENV` → `ARQUANTIX_ENV` → `ENVIRONMENT` → `ENV`, puis alias `prod` → `production`, etc.).

### Usages identifiés

| Zone | Rôle |
|------|------|
| `AUTH_RL_BACKEND` | `memory` \| `redis` \| `auto` — choix du backend côté `auth_rate_limit.build_auth_rate_limiter`. |
| `is_auth_redis_required_env()` | Décide si le **bootstrap** impose `redis` + ping, et si `build_auth_rate_limiter` est en chemin « prod » (Redis obligatoire, pas de memory). |
| `enforce_auth_infrastructure_bootstrap` | Après `validate_security_environment_startup`, vérifie `AUTH_RL_BACKEND=redis` et `ping_auth_redis()` lorsque Redis est requis. |
| `validate_security_environment_startup` | Rejette OTP dev / fake SMS lorsque Redis auth est requis (aligné sur la même stratégie). |
| `auth_rate_limit.py` | `is_production_environment()` → alias de `is_auth_redis_required_env()` pour le limiteur. |

### Dépendance `ENVIRONMENT` / `ENV`

- **Legacy** : seule source pour « prod Redis » tant que `AUTH_REDIS_ENV_STRATEGY=legacy` (défaut).
- **`APP_ENV`** : source métier pour la normalisation ; prise en compte pour Redis obligatoire uniquement en mode `normalized`.

---

## Problems

1. **Divergence intentionnelle** : `APP_ENV=production` sans `ENVIRONMENT=production` ne déclenchait pas l’exigence Redis (legacy), alors que l’équipe considère `APP_ENV` comme label métier principal.
2. **Double étiquette** : certains stacks fixent `ENVIRONMENT`, d’autres `APP_ENV` — risque de mauvaise interprétation sans documentation et sans bascule progressive.
3. **Staging** : en mode `normalized`, seul **`production`** normalisé exige Redis (pas `staging`), ce qui peut différer du legacy si `ENVIRONMENT=staging` était utilisé autrement — à valider par équipe ops.

---

## New Model

### API (`services/security/security_env.py`)

| Fonction | Description |
|----------|-------------|
| `auth_redis_env_strategy()` | Retourne `legacy` ou `normalized` (défaut `legacy`). |
| `is_auth_redis_required_env_legacy()` | Règle historique `ENVIRONMENT` / `ENV`. |
| `is_auth_redis_required_env_target()` | Cible : `get_normalized_app_env() == "production"`. |
| `is_auth_redis_required_env()` | Dispatch selon la stratégie. |

### Variable d’environnement

- **`AUTH_REDIS_ENV_STRATEGY`** : `legacy` \| `normalized` (alias `normalised` accepté). Valeur inconnue → **warning** + fallback **`legacy`** (sécurité prod).

### Bootstrap

- Log **INFO** unique au démarrage : stratégie, `legacy_redis_required`, `normalized_production_target`, `effective_redis_required`.
- Messages d’erreur `RuntimeError` alignés sur la stratégie effective (plus seulement « ENVIRONMENT/ENV »).

---

## Migration Strategy

1. **Phase actuelle (déployée dans le code)** : défaut **`legacy`** — **aucun changement** pour les déploiements existants sans nouvelle variable.
2. **Pré-production / nouveaux clusters** : poser `APP_ENV=production` **et** `AUTH_REDIS_ENV_STRATEGY=normalized` une fois `ENVIRONMENT`/`APP_ENV` alignés avec la convention voulue.
3. **Bascule progressive** : par environnement (staging pilote → prod), pas par utilisateur.
4. **Critères de bascule** :
   - `APP_ENV` (ou chaîne normalisée) est la source de vérité documentée pour l’équipe.
   - `ENVIRONMENT` est aligné ou abandonné pour ce critère (selon infra).
5. **Rollback** : retirer `normalized` ou fixer `AUTH_REDIS_ENV_STRATEGY=legacy` (retour immédiat au comportement historique).

---

## Risks

| Risque | Mitigation |
|--------|------------|
| Prod exige Redis alors que l’équipe pensait être en « dev » | Défaut `legacy` ; bascule `normalized` volontaire et documentée. |
| `APP_ENV=production` + `ENVIRONMENT=development` + `normalized` → Redis obligatoire | Comportement voulu pour la cible ; vérifier secrets et `AUTH_REDIS_URL`. |
| Logs / messages d’erreur différents | Acceptable ; messages référencent `AUTH_REDIS_ENV_STRATEGY`. |
| Tests / CI | Couverture : legacy inchangé, normalized + cas sans `ENVIRONMENT`. |

---

## Rollout Plan

1. **Merger** le code avec défaut `legacy` (aucune action ops requise).
2. **Documenter** dans le runbook interne la variable `AUTH_REDIS_ENV_STRATEGY` et les deux modes (ce fichier + `.env.security.example`).
3. **Staging** : `AUTH_REDIS_ENV_STRATEGY=normalized`, `APP_ENV=staging` ou `production` selon cas — valider que Redis est bien présent quand attendu.
4. **Production** : après validation staging, activer `normalized` sur un sous-ensemble ou directement selon maturité.
5. **Obsolète à terme** : envisager de retirer le mode `legacy` dans une version majeure **après** migration complète des déploiements (non planifié ici).

---

## Références code

- `api/services/security/security_env.py` — logique stratégie et prédicats.
- `api/services/auth/auth_bootstrap.py` — `enforce_auth_infrastructure_bootstrap`, logs.
- `api/services/auth/auth_rate_limit.py` — `is_production_environment()` / limiteur.
- `api/tests/test_security_env.py` — tests legacy / normalized / absence `ENVIRONMENT`.
