# Guide environnements et flags sécurité (Arquantix API)

Document de référence pour développeurs et DevOps. La logique centralisée vit dans `api/services/security/security_env.py` (à jour avec le code).

---

## Quick Start

1. **Fixer l’environnement** avec `APP_ENV` (valeur canonique : `development`, `test`, `staging`, `production`).
2. **Ne pas mélanger** les objectifs : une variable sert à *nommer* l’environnement métier ; d’autres règles (Redis, OTP) suivent des règles précises décrites ci‑dessous.
3. **En prod / préprod**, activer Redis pour le rate limit auth (`AUTH_RL_BACKEND=redis` + `AUTH_REDIS_URL`) lorsque l’API considère que Redis est **obligatoire** (voir [Redis vs OTP](#redis-rate-limit-auth-vs-règles-otp--2fa)).
4. **Avant un merge** : parcourir la [checklist](#checklist-avant-push--déploiement).

---

## Environment Model

### Standard officiel : valeurs d’environnement

L’API lit une **chaîne d’identité** dans cet ordre (première valeur non vide gagne) :

`APP_ENV` → `ARQUANTIX_ENV` → `ENVIRONMENT` → `ENV`

Ensuite elle **normalise** la valeur vers une étiquette interne (minuscules, alias connus).

**Valeurs canoniques recommandées** (à utiliser dans les configs et la doc interne) :

| Canonique     | Usage typique                          |
|---------------|----------------------------------------|
| `development` | Machine locale, équipe                 |
| `test`        | CI, tests automatisés explicites       |
| `staging`     | Préproduction, recette                 |
| `production`  | Production utilisateurs                |

> Si **aucune** de ces variables n’est définie, le comportement par défaut équivaut à **`development`** (non « prod-like » pour la 2FA).

### Alias acceptés (mais déconseillés)

Le code les comprend et les mappe vers le canonique — **préférez toujours le nom canonique** dans les fichiers d’env partagés et l’infra.

| Alias (exemple) | Devient   |
|-------------------|-----------|
| `dev`, `local`    | `development` |
| `testing`         | `test`    |
| `stage`           | `staging` |
| `prod`, `live`    | `production` |

**Pourquoi les éviter ?** Moins ambigu pour les humains, logs et runbooks ; évite les « je croyais que prod était déjà production ».

### Deux notions à ne pas confondre

**`production` (strict)**  
- `get_normalized_app_env() == "production"`  
- Exemple : stratégie Redis **normalized** : Redis obligatoire seulement ici.

**« Prod-like » (`is_production_like_env`)**  
- Environnement **normalisé** = `production` **ou** `staging`.  
- Sert surtout pour : interdiction des OTP « dev » exposés, fake SMS, assouplissements 2FA — **même rigueur staging que prod** sur ces points.

En résumé : **staging est traité comme prod pour la sécurité OTP / fournisseurs**, mais ce n’est pas la même chose que « instance Redis obligatoire » selon la stratégie (voir ci‑dessous).

---

## Règles clés (sans jargon)

### Redis (rate limit auth) vs règles OTP / 2FA

Ce sont **deux axes différents** :

| Sujet | Question | Règle courte |
|-------|----------|--------------|
| **OTP / SMS / e-mail / passkeys « strict »** | Est-ce que je suis en **prod-like** ? | Basé sur **`APP_ENV` (normalisé)** : `production` ou `staging` → règles strictes (pas de dev OTP, pas de fake SMS, etc.). |
| **Redis obligatoire pour le rate limit login/refresh** | L’API refuse-t-elle de tourner sans Redis distribué ? | Contrôlé par **`AUTH_REDIS_ENV_STRATEGY`** : voir ci‑dessous. |

**Stratégie Redis (`AUTH_REDIS_ENV_STRATEGY`, défaut `legacy`)**

- **`legacy`** (défaut, compatible anciens déploiements) : Redis obligatoire si **`ENVIRONMENT` ou `ENV`** vaut `production`, `prod` ou `live` — **sans** se baser sur `APP_ENV` seul. Utile quand seul `ENVIRONMENT` est posé par l’orchestrateur.
- **`normalized`** : Redis obligatoire si l’environnement **normalisé** est **`production`** (via la chaîne `APP_ENV` → …).

Voir aussi : `REDIS_ENV_HARMONIZATION_PLAN.md`.

**Variables utiles** : `AUTH_RL_BACKEND` (`memory` | `redis` | `auto`), `AUTH_REDIS_URL`, `AUTH_REDIS_ENV_STRATEGY`.

### Mode dev OTP (codes fixes / exposés)

Réservé aux environnements **non prod-like** (donc pas `production` ni `staging` au sens normalisé).

| Variable | Rôle |
|----------|------|
| `TWO_FACTOR_DEV_FIXED_CODE` | Code OTP fixe (6 chiffres) si non prod-like |
| `TWO_FACTOR_DEV_EXPOSE_CODE` | Exposer le code dans les réponses (ex. JSON `dev_code`) |
| `TWO_FACTOR_RELAXED` | Assouplit encore les garde-fous 2FA si `true` |

**Au démarrage**, si Redis auth est requis pour l’environnement, ces flags dangereux doivent être absents / faux (sinon erreur).

### Fournisseurs « noop » (SMS / e-mail factice)

En **prod-like** (`staging` ou `production`), un SMS factice (`FAKE_SMS_PROVIDER`) est **interdit** (erreur au boot si activé). Les vrais flux OTP doivent utiliser de vrais connecteurs.

### Passkeys et WebAuthn « strict »

- **`AUTH_PASSKEYS_ENABLED`** : activer les passkeys (défaut **activé** si non désactivé explicitement).
- **`is_webauthn_strict_environment()`** : vrai si environnement **prod-like** **ou** si `WEBAUTHN_STRICT_CONFIG=true`. En pratique : en staging/production, la config WebAuthn (HTTPS, RP ID, origines) doit être cohérente.

Variables courantes : `WEBAUTHN_RP_ID`, `WEBAUTHN_ORIGINS`, `WEBAUTHN_STRICT_CONFIG`, `WEBAUTHN_PUBLIC_BASE_URL` (voir config WebAuthn du projet).

---

## Security Flags

Tous les défauts ci‑dessous correspondent au **code** (`security_env.py`). « Recommandé » = usage usuel par type d’environnement.

### OTP (mobile & admin)

| Variable | Rôle | Défaut | Recommandation |
|----------|------|--------|----------------|
| `AUTH_MOBILE_OTP_LOGIN_ENABLED` | OTP SMS côté mobile login | `false` | `true` en staging/prod si produit activé |
| `AUTH_ADMIN_EMAIL_OTP_ENABLED` | OTP e-mail admin | `false` | `true` si besoin ; en prod-like un vrai provider e-mail est requis si activé |

### Passkeys

| Variable | Rôle | Défaut | Recommandation |
|----------|------|--------|----------------|
| `AUTH_PASSKEYS_ENABLED` | Feature passkeys | `true` (opt-out) | `true` prod ; désactiver seulement pour debug ciblé |

### Événements & observabilité

| Variable | Rôle | Défaut | Recommandation |
|----------|------|--------|----------------|
| `AUTH_SECURITY_EVENTS_ENABLED` | Persistance événements sécurité | `true` | `true` staging/prod |
| `SECURITY_EVENTS_SINK` | Export SIEM (`datadog`, `opensearch`, `none`, …) | `none` | Configurer en prod si SIEM |

### Stratégie login & appareil

| Variable | Rôle | Défaut | Recommandation |
|----------|------|--------|----------------|
| `LOGIN_DEVICE_TRUST_ENABLED` | Profil confiance appareil | `true` | `true` |
| `LOGIN_AUTH_STRATEGY_ENABLED` | Orchestration stratégie login | `true` | `true` |
| `AUTH_DEVICE_FINGERPRINT_ENABLED` | Header empreinte device | `true` | `true` sauf debug |

### Adaptive auth, session, auth continue

| Variable | Rôle | Défaut | Recommandation |
|----------|------|--------|----------------|
| `ADAPTIVE_AUTH_ENABLED` | Orchestrateur adaptatif | `false` | Activer progressivement si produit |
| `SESSION_INTELLIGENCE_ENABLED` | Intelligence par session | `false` | Idem |
| `CONTINUOUS_AUTH_ENABLED` | Auth continue (actions sensibles) | `false` | Idem ; nécessite souvent session intelligence |

### Rate limiting auth

| Variable | Rôle | Défaut | Recommandation |
|----------|------|--------|----------------|
| `AUTH_RL_BACKEND` | `memory` / `redis` / `auto` | `auto` (hors bootstrap) | **`redis`** quand Redis requis ; `AUTH_REDIS_URL` défini |
| `AUTH_REDIS_ENV_STRATEGY` | `legacy` / `normalized` | `legacy` | Voir harmonisation Redis ; `normalized` pour nouvelle convention `APP_ENV`-centric |
| `AUTH_RL_LOGIN_MAX`, `AUTH_RL_LOGIN_WINDOW_SEC`, … | Quotas | voir `auth_rate_limit.py` | Ajuster selon charge |

---

## Examples

### `.env` development minimal

Objectif : tourner en local sans Redis strict, avec assouplissements possibles.

```env
APP_ENV=development

# Optionnel : rate limit en mémoire
AUTH_RL_BACKEND=auto
# Pas de AUTH_REDIS_URL nécessaire si Redis non imposé

# Ne pas activer en prod-like :
# TWO_FACTOR_DEV_FIXED_CODE=111111
# TWO_FACTOR_DEV_EXPOSE_CODE=true
```

### `.env` staging

Objectif : **même discipline sécurité que la prod** pour OTP / fake SMS ; Redis selon stratégie.

```env
APP_ENV=staging

# Si l’infra utilise encore legacy pour Redis :
ENVIRONMENT=staging
AUTH_REDIS_ENV_STRATEGY=legacy
AUTH_RL_BACKEND=redis
AUTH_REDIS_URL=redis://…

AUTH_SECURITY_EVENTS_ENABLED=true
FAKE_SMS_PROVIDER=false
```

### `.env` production

Objectif : Redis distribué, pas de mode dev OTP, fournisseurs réels.

```env
APP_ENV=production

# Souvent encore requis avec AUTH_REDIS_ENV_STRATEGY=legacy :
ENVIRONMENT=production

AUTH_REDIS_ENV_STRATEGY=legacy
AUTH_RL_BACKEND=redis
AUTH_REDIS_URL=redis://…

FAKE_SMS_PROVIDER=false
# TWO_FACTOR_DEV_FIXED_CODE et TWO_FACTOR_DEV_EXPOSE_CODE absents ou false

# WebAuthn : valeurs réelles
# WEBAUTHN_RP_ID=…
# WEBAUTHN_ORIGINS=https://…
```

*(Pour une prod qui bascule en `AUTH_REDIS_ENV_STRATEGY=normalized`, aligner `APP_ENV=production` et la doc interne — voir `REDIS_ENV_HARMONIZATION_PLAN.md`.)*

---

## Common Mistakes

| Erreur | Pourquoi c’est embêtant | Que faire |
|--------|-------------------------|-----------|
| Mettre `APP_ENV=dev` au lieu de `development` | Fonctionne (alias), mais brouille les runbooks | Utiliser `development` dans les env partagés |
| Croire que `APP_ENV=production` suffit **toujours** pour imposer Redis | En **`legacy`**, Redis regarde surtout `ENVIRONMENT`/`ENV` | Poser `ENVIRONMENT=production` **ou** passer en `AUTH_REDIS_ENV_STRATEGY=normalized` |
| Laisser `TWO_FACTOR_DEV_EXPOSE_CODE=true` ou un code fixe sur un env qui exige Redis / prod-like | **Crash au démarrage** ou fuite de sécurité | Désactiver / retirer ces variables en staging/prod |
| Activer `FAKE_SMS_PROVIDER=true` en **staging** ou **production** | Interdit (`is_production_like_env`) | `false` + vrai provider Twilio / équivalent |
| Désactiver passkeys par erreur (`AUTH_PASSKEYS_ENABLED=false`) alors que le produit les attend | Régression fonctionnelle | Vérifier le défaut et l’intention |
| Variables dupliquées sans ordre de priorité compris | Comportement « surprenant » | Se rappeler : `APP_ENV` bat `ENVIRONMENT` pour le **nom** métier normalisé, pas pour la règle Redis en mode **legacy** |

---

## Checklist (avant push / déploiement)

- [ ] **`APP_ENV`** (ou fallback explicite) correspond à l’intention : `development` / `test` / `staging` / `production`.
- [ ] **Pas d’alias** ambigus dans les fichiers **partagés** (préférer les noms canoniques).
- [ ] **Redis** : `AUTH_RL_BACKEND` + `AUTH_REDIS_URL` cohérents avec **`AUTH_REDIS_ENV_STRATEGY`** et l’infra (`ENVIRONMENT` si `legacy`).
- [ ] **Pas de mode dev OTP** (`TWO_FACTOR_DEV_*`) sur **staging/production**.
- [ ] **`FAKE_SMS_PROVIDER`** désactivé en prod-like.
- [ ] **WebAuthn** : RP ID / origines alignés avec l’URL réelle en staging/prod.
- [ ] **Flags optionnels** (adaptive, session intelligence, …) alignés avec le produit et la capacité à les supporter.

---

## Références rapides

| Fichier | Contenu |
|---------|---------|
| `api/services/security/security_env.py` | Source de vérité code |
| `api/.env.security.example` | Liste de variables commentée |
| `REDIS_ENV_HARMONIZATION_PLAN.md` | Redis `legacy` vs `normalized` |

*Document prêt à partager — à versionner avec le dépôt.*
