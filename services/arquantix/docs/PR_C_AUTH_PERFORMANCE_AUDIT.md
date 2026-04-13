# PR C — Audit performance auth (accès DB)

Objectif : recenser où la base est sollicitée pour l’authentification / résolution d’identité, et ce qui est optimisable sans affaiblir PR A (rotation) ni PR B (device binding).

## Principes

- **Format JWT** : inchangé.
- **Vérité session / révocation / device** : toujours via chemins existants qui interrogent `AuthSession`, refresh tokens, etc.
- **Cache PR C** : uniquement identifiants **peu volatils** (`person_id` par `admin_user_id`, `client_id` par `person_id`), TTL mémoire, pas d’états sécurité dynamiques.

## Tableau — fonctions / routes

| Route / fonction | Appels DB typiques | Données utilisées | Optimisable (PR C) |
|------------------|-------------------|-------------------|---------------------|
| `resolve_auth_context_jwt_only` | **0** | `sub` → `admin_user_id`, `person_id`/`pid`, `sid` | N/A (déjà optimal) |
| `resolve_auth_context_with_cache` / `strict_db` | **1+** via `_get_current_user_internal` | `AdminUser`, validation session/device selon auth existant | Partiel : après 1ère résolution, cache identité pour **client** ; DB toujours pour valider le user |
| `auth.get_current_user` | **strict_db** | Idem + rôle ZT / contrôles | Reste **strict DB** (niveau 3) |
| `dependencies.get_current_user_or_admin` | **strict_db** + **0 ou 1** `Client` | `AdminUser`, `Client.id` si person liée | **Client** : 2e appel souvent **cache hit** (`get_client_id_for_person_cached`) |
| `identity_cache.get_person_id_cached` | **0** (lecture cache) | `person_id` ou sentinelle miss | Alimenté par `warm_identity_caches_from_user_db` après DB user |
| `identity_cache.get_client_id_for_person_cached` | **0** si hit, **1** `Client` si miss | `client_id` | Oui (TTL) |
| `auth` refresh / revoke / login | **multiple** (sessions, tokens, rate limits) | Session, rotation | **Non** — restent chemins DB complets (sensibles) |
| `security.deps._person_from_jwt` | **0** si `person_id`/`pid` dans JWT ; sinon résolution `sub` | `person_id` | Chemin JWT : **0 DB** pour person ; `resolve_person_id` fait encore **`Person` lookup** (anti-énumération / existence) |
| `security.deps.resolve_person_id` | **1** `Person` minimum | existence personne | **Strict** (volontaire) |

## Synthèse des gains mesurables

- **Réduction** : lectures répétées de `Client` par `person_id` sur les routes utilisant `get_current_user_or_admin` (identité / KYC) lorsque le cache TTL est chaud.
- **Non réduction** : première requête par fenêtre TTL ; toute validation qui dépend de l’état serveur (`AdminUser`, session) dans `_get_current_user_internal`.

## Liste des « DB hits » ciblés par PR C

| Avant (schéma) | Après |
|----------------|--------|
| `Client` par requête pour enrichir `AuthContext` | Souvent **cache hit** après warm ou appel précédent |
| — | `get_person_id_cached` prêt pour extensions futures (clé `auth:admin_user_person:{id}`) |

Les hits **AdminUser** par requête sur les dépendances **strict_db** sont inchangés par design (sécurité).
