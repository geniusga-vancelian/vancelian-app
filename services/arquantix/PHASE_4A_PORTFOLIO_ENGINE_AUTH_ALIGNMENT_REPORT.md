# Phase 4A — Alignement du modèle d’auth (Portfolio Engine)

## Executive Summary

Le **Portfolio Engine** utilise aujourd’hui **deux familles de garde-fous** :

1. **`ActorContext`** (`X-Actor-Type`, `X-Actor-Id`, `X-Actor-Roles`) — RBAC + **ownership** via `require_portfolio_access` / `AuthorizationService`.
2. **JWT Bearer + `AdminUser`** — notamment `require_continuous_auth_for_action(...)` (Phases 1–4) sur les mutations sensibles (ex. `wallet_transfer`).

Cette dualité est **intentionnelle dans l’historique** (headers « acteur » pour le moteur interne / back-office), mais crée une **protection inégale** : l’auth continue ne s’applique **pas** là où seul `ActorContext` est présent, et **aucun JWT n’est exigé** sur ces routes.

**Livrable Phase 4A (conservateur) :**

- Rapport d’audit + matrice de classification par routeur.
- **Migrations minimales** sur trois **GET sensibles** qui étaient **ouverts ou incohérents** avec le reste du périmètre « portfolio-scoped » :
  - `GET .../portfolios/{portfolio_id}/summary`
  - `GET .../positions/{position_id}/valuation`
  - `GET .../orchestration-runs/{run_id}`

Ces endpoints appliquent désormais le **même modèle d’ownership** que `GET .../portfolios/{portfolio_id}/valuation` (déjà protégé).

---

## Légende de classification

| Classe | Définition |
|--------|------------|
| **JWT_ONLY** | Dépendance impliquant `get_current_user` / `AdminUser` (Bearer), **sans** `ActorContext` obligatoire dans la route. |
| **ACTOR_CONTEXT_ONLY** | `get_actor_context` et/ou `require_portfolio_access` / `require_admin_or_ops`, **sans** `require_continuous_auth_for_action`. |
| **JWT_PLUS_ACTOR_CONTEXT** | Les **deux** : typiquement `require_continuous_auth_for_action` **et** `_guard` / `require_portfolio_access`. |
| **PUBLIC_OR_LOW_RISK** | Aucune dépendance d’auth explicite (souvent TODO « wire auth ») ou donnée catalogue / placeholder. |

**Sensibilité (indicatif) :** *High* = positions, NAV, exécutions, ordres ; *Medium* = produits / instruments catalogue ; *Low* = placeholder, métadonnées techniques.

---

## Matrice synthétique (par module router)

Préfixe API commun : **`/api/portfolio-engine`** (voir `router.py`).

| method | path (suffixe) | Router (fichier) | Modèle d’auth | Sensibilité | Cible recommandée | Commentaire |
|--------|----------------|------------------|---------------|-------------|-------------------|-------------|
| GET | `/clients` … `/clients/{id}` … | clients/router | Mix : la plupart **PUBLIC** (TODO auth) ; **identity** = JWT + AuthContext + continuous | High pour identity | JWT + ownership / continuous pour lectures sensibles | Identity déjà Phase 4 ; CRUD client encore ouvert |
| GET | `/executions`, `/executions/{id}` | execution/router | **PUBLIC** (pas d’actor) pour GET ; POST = **JWT_PLUS_ACTOR** | High | Migrer GET vers ACTOR ou JWT+ACTOR | Forte surface d’info d’exécution |
| POST | `/executions` … | execution/router | **JWT_PLUS_ACTOR** | High | Maintenir | Aligné Phase 3 |
| GET/POST | `/orders` … | orders/router | GET list/detail : **ACTOR** ; mutations : **JWT_PLUS_ACTOR** | High | Harmoniser (voir § recommandations) | Incohérence GET vs POST |
| GET/POST | `/trades` … | trades/router | Idem orders | High | Idem | |
| GET/POST | `/settlements` … | settlement/router | Idem | High | Idem | |
| GET | `/portfolios/{id}/summary` | summary/router | **ACTOR** via `require_portfolio_access` (**migré 4A**) | High | **ACTOR** (+ JWT futur optionnel) | Était PUBLIC — corrigé |
| GET | `/portfolios/{id}/valuation` | valuations/router | **ACTOR** `require_portfolio_access` | High | Maintenir | Référence ownership |
| GET | `/positions/{id}/valuation` | valuations/router | **ACTOR** `require_position_portfolio_access` (**migré 4A**) | High | **ACTOR** | Aligné sur portfolio valuation |
| POST | `/portfolios/{id}/valuation/snapshot` | valuations/router | **ACTOR** + `_guard` | High | Maintenir | |
| GET | `/portfolios/{id}/orchestration-runs` | orchestrator/router | **ACTOR** `require_portfolio_access` | Medium | Maintenir | |
| GET | `/orchestration-runs/{run_id}` | orchestrator/router | **ACTOR** `require_orchestration_run_portfolio_access` (**migré 4A**) | Medium | **ACTOR** | Fermeture IDOR |
| POST | `/portfolios/{id}/orchestrate` | orchestrator/router | **JWT_PLUS_ACTOR** + portfolio access | High | Maintenir | |
| GET | `/portfolios` … nested | portfolios/router | Liste/filtre via **ACTOR** ; beaucoup de GET sans JWT | High | JWT+ACTOR pour prod client | `get_actor_context` partout |
| GET | performance, drift | performance/router, drift/router | **ACTOR** `require_portfolio_access` | High | Maintenir | |
| GET/POST | `/admin/*` jobs, recon, scheduler | hardening/* | **ACTOR** `_guard` (admin/ops) | High / ops | **Interne** ou JWT service-to-service | Pas d’auth JWT utilisateur |
| GET/POST | bundles (admin) | bundles/router | **ACTOR** `_guard` | High | Interne / admin | |
| GET/POST | subscriptions | subscriptions/router | Majoritairement **PUBLIC** ; provision = **ACTOR** | High | Migrer vers ACTOR + JWT pour tout CRUD | Dette connue |
| GET | instruments, assets, products (catalog) | divers | Souvent **PUBLIC** | Low–Medium | Laisser ou ACTOR lecture | Catalogue vs compte |
| GET | `/snapshots` | snapshots/router | **PUBLIC** placeholder | Low | N/A | TODO impl |

*(Les routeurs non listés ligne à ligne suivent le même schéma : la majorité des **CRUD** « atomiques » sont **PUBLIC_OR_LOW_RISK** avec TODO `get_current_user` dans le code.)*

---

## Analyse des routes **ACTOR_CONTEXT_ONLY**

| Sous-type | Description | Exemples |
|-----------|-------------|----------|
| **Service / back-office interne** | Appelées par workers, ops, outils avec en-têtes `X-Actor-Roles: admin|ops` | `hardening/jobs`, `reconciliation`, `scheduler`, `bundles` admin |
| **À migrer vers JWT + Actor (futur)** | Exposition **client** ou **conseiller** : aujourd’hui seuls les headers identifient l’acteur ; un **JWT** pourrait porter le même sujet + auth continue | `list_portfolios`, lectures positions, drift, performance |
| **Legacy / dette** | Endpoints sans auth explicite — **PUBLIC** | `subscriptions` GET, `wallets` GET, `executions` GET, nombreux `TODO: wire auth` |

---

## Migrations réalisées (Phase 4A)

| Endpoint | Avant | Après |
|----------|-------|--------|
| `GET /api/portfolio-engine/portfolios/{portfolio_id}/summary` | Aucune auth | `require_portfolio_access` (ACTOR + ownership) |
| `GET /api/portfolio-engine/positions/{position_id}/valuation` | Aucune auth côté ownership | `require_position_portfolio_access` |
| `GET /api/portfolio-engine/orchestration-runs/{run_id}` | Lecture par `run_id` sans contrôle client | `require_orchestration_run_portfolio_access` |

**Fichiers modifiés**

- `api/services/portfolio_engine/hardening/authorization/dependencies.py` — nouvelles dépendances `require_position_portfolio_access`, `require_orchestration_run_portfolio_access`.
- `api/services/portfolio_engine/summary/router.py`
- `api/services/portfolio_engine/valuations/router.py`
- `api/services/portfolio_engine/orchestrator/router.py`
- `api/tests/test_portfolio_engine_hardening_authorization.py` — tests unitaires sur les nouvelles dépendances.

**Breaking change :** les appelants de ces trois GET **doivent** envoyer les en-têtes `X-Actor-*` cohérents avec les autres endpoints portfolio-scoped (comme `/portfolios/{id}/valuation`). Les rôles **bypass** (`admin`, `ops`, `system` dans `X-Actor-Roles`) restent alignés sur `AuthorizationService`.

---

## Candidats migration (priorisés, non tous faits)

### Migrer **maintenant** (prochaine micro-vague, hors 4A si besoin)

- **GET** `executions`, `execution/{id}` — ajouter au minimum `require_admin_or_ops` ou scoping métier.
- **Subscriptions** — GET liste / détail : ajouter `require_portfolio_access` ou contrôle par `client_id` (selon modèle de données).

### Garder **ACTOR-only** pour l’instant

- **`/api/portfolio-engine/admin/*`** (jobs, reconciliation, scheduler) — usage **interne** ; ajouter plutôt **mTLS / token machine** dans une phase « service auth » que JWT utilisateur.

### Déprécier plus tard

- Endpoints **placeholder** (`snapshots`) ou doubles chemins non utilisés après migration clients.

---

## Recommandation architecturale

1. **Ne pas** remplacer `ActorContext` par JWT partout en une seule PR : le moteur portfolio s’appuie sur **ownership** (client / conseiller) déjà exprimé dans `AuthorizationService`.
2. **Cible cible (North Star)** : **JWT** (identité + session + continuous auth) **+** **claims ou en-têtes** dérivés pour reconstruire un `ActorContext` **côté API** (un seul contexte « sujet »), plutôt que deux silos parallèles.
3. **Court terme** : pour toute lecture **financière** (positions, NAV, exécutions), appliquer au minimum **`require_portfolio_access`** ou un dérivé (comme en 4A) ; ajouter **JWT + continuous** sur les chemins **exposés au mobile / web** quand le client utilise déjà Bearer.

---

## Tests

- `pytest tests/test_portfolio_engine_hardening_authorization.py` — **OK** (inclut les nouveaux cas position + orchestration run).

---

## Synthèse

| Élément | Statut |
|---------|--------|
| Ambiguï JWT vs Actor | Documentée ; matrice fournie |
| GET sensibles alignés ownership | 3 routes migrées |
| Routes volontairement Actor-only | Admin hardening, jobs, scheduler |
| Prochaine étape | Décision produit sur JWT+Actor unifié pour le client mobile vs services internes |
