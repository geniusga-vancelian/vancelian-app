# Analyse de la Stack Technique Arquantix

**Date:** 2026-01-12  
**Basé sur:** Analyse du codebase existant

---

## 1. Backend Stack

### Langage & Framework
- **Langage:** Python 3.9+
- **Framework:** FastAPI uniquement
- **Style API:** REST uniquement (pas de GraphQL/WebSocket visible)
- **Authentification:** 
  - JWT (HS256) avec secret partagé (`JWT_SECRET_KEY`)
  - Secret chargé depuis `.env.local` puis `.env` (priorité)
  - Token expiration: 24 heures
  - OAuth2PasswordBearer scheme
  - bcrypt pour le hashage des mots de passe

### Observations
- Pas de services Python supplémentaires identifiés
- Pas de WebSocket ou GraphQL
- Secret JWT partagé entre API et Web (Next.js génère aussi des JWT)

---

## 2. Database Layer

### Base de Données
- **Primary DB:** PostgreSQL 15 (arquantix-db)
- **Deux bases distinctes:**
  - `arquantix_quant` (API) - port 5443
  - `arquantix_admin` (Web/Prisma) - port 5443

### ORM / Migrations
- **API (FastAPI):** SQLAlchemy + Alembic
- **Web (Next.js):** Prisma + Prisma Migrate
- **Stratégie:** Dual ORM (volontaire ou historique ?)

### UUID Strategy
- **API (SQLAlchemy):** `Integer` auto-increment (SERIAL)
  - Tous les modèles utilisent `Column(Integer, primary_key=True)`
  - Exemples: `AdminUser.id`, `Page.id`, `MarketDataInstrument.id`
  
- **Web (Prisma):** `String` avec `@default(cuid())`
  - Exemples: `User.id`, `Page.id`, `Section.id`
  - CUID = Collision-resistant Unique Identifier (format: `clxxx...`)

### ⚠️ Problème de Cohérence Identifié
- **Incohérence majeure:** API utilise Integer, Web utilise CUID String
- Les deux systèmes pointent vers des bases différentes mais partagent potentiellement des données
- Pas de stratégie unifiée pour les IDs

### Schémas de Base de Données
- API: `public` schema explicite dans certains modèles
- Web: Pas de schéma explicite dans Prisma (défaut: `public`)

---

## 3. Infrastructure

### Hébergement & Runtime
- **Non déterminé depuis le code**
- Variables d'environnement pour configuration
- Docker utilisé localement (arquantix-db container)

### Stockage
- **Media:** Configuration `STORAGE_BACKEND` (local par défaut)
- `MEDIA_BASE_URL` configurable
- Uploads locaux dans `api/uploads/`
- Pas de S3/R2 visible dans le code actuel

### Secrets Management
- **Approach actuel:** Variables d'environnement (`.env.local` + `.env`)
- Pas d'AWS Secrets Manager visible
- Priorité: `.env.local` > `.env`

---

## 4. Frontend / Admin

### Frontend
- **Framework:** Next.js (confirmé)
- **TypeScript:** Oui (fichiers `.ts`/`.tsx`)

### Admin Tooling
- **Approach:** Custom admin avec React Admin
- **Pas de Retool** identifié
- Routes admin: `/admin/*`

### Formulaires
- **Approach:** Schema-driven (Zod pour validation)
- Exemple: `composeEmailUGGSchema` dans `compose-ugg/route.ts`
- React Admin pour les formulaires admin

---

## 5. Compliance & Audit

### Audit Trail
- **Append-only:** ❌ Non implémenté
- **Champs d'audit présents:**
  - `created_at`, `updated_at` (timestamps)
  - `created_by_user_id` (dans certains modèles)
  - Pas de table d'audit dédiée

### Rétention
- **Règles définies:** ❌ Non visible dans le code

### Chiffrement
- **At rest:** Non déterminé
- **In transit:** HTTPS (assumé, pas de config visible)

### Juridictions
- **Non déterminé** depuis le code

---

## 6. External Providers

### KYC / AML
- **KYC:** ❌ Non intégré
- **AML/Screening:** ❌ Non intégré
- **Banking/Payments:** ❌ Non intégré

### Providers Actuels
- **Market Data:** Yahoo Finance, Alpha Vantage
- **AI:** OpenAI (pour traduction et génération d'emails)

---

## 7. Contraintes Codebase

### Structure Repo
```
arquantix/
├── api/          # FastAPI (Python)
│   ├── alembic/  # Migrations
│   ├── app/      # Application code
│   ├── services/ # Business logic
│   └── tests/    # Tests
├── web/          # Next.js (TypeScript)
│   ├── prisma/   # Prisma schema & migrations
│   └── src/      # Source code
└── scripts/      # Shell scripts
```

### Naming Conventions
- **Python (API):** `snake_case`
  - Variables: `user_email`, `created_at`
  - Fonctions: `get_current_user`, `create_access_token`
  - Classes: `AdminUser`, `MarketDataInstrument`
  
- **TypeScript (Web):** `camelCase` (Prisma)
  - Variables: `userId`, `createdAt`
  - Fonctions: `getSessionFromCookie`
  - Types: `ComposeEmailUGGRequest`

### Dette Technique Identifiée

1. **Dual ORM (SQLAlchemy + Prisma)**
   - Deux systèmes de migration
   - Risque de désynchronisation
   - Deux bases de données séparées

2. **Incohérence des IDs**
   - Integer (API) vs CUID String (Web)
   - Impossible de partager des données directement

3. **Classes EmailModule manquantes**
   - `modules_resolver.py` importe des classes qui n'existent pas
   - Workaround: import conditionnel ajouté

4. **Pas d'audit trail**
   - Pas de traçabilité des modifications
   - Pas de compliance ready

5. **Secrets en variables d'environnement**
   - Pas de rotation automatique
   - Pas de gestion centralisée

---

## Recommandations pour Alignement

### Priorité 1: Unifier la Stratégie d'IDs
- **Option A:** Migrer API vers UUIDv4 (app-generated)
- **Option B:** Migrer Web vers Integer (si bases peuvent fusionner)
- **Option C:** Garder séparé mais documenter clairement

### Priorité 2: Audit Trail
- Ajouter table `audit_logs` (append-only)
- Champs: `entity_type`, `entity_id`, `action`, `user_id`, `timestamp`, `changes_json`
- Triggers PostgreSQL pour auto-logging

### Priorité 3: Compliance Ready
- Chiffrement at rest (si requis)
- Rétention policies
- Juridictions supportées

### Priorité 4: External Providers
- Intégration KYC/AML si requis
- Banking/Payments si requis

---

## Questions Ouvertes pour Confirmation

1. **Dual ORM:** Est-ce volontaire ou historique ? Faut-il unifier ?
2. **Bases séparées:** Pourquoi `arquantix_quant` vs `arquantix_admin` ?
3. **UUID Strategy:** Quelle stratégie cible pour les nouveaux modèles ?
4. **Infrastructure:** AWS/GCP/Azure ? ECS/K8s/Serverless ?
5. **Compliance:** Quelles juridictions cibles ? Audit requis ?
6. **KYC/AML:** Intégration prévue ? Quels providers ?

---

**Prochaines étapes:** Attendre confirmation avant de proposer des schémas spécifiques.
