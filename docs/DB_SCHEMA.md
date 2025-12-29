# Schéma Base de Données - Vancelian App

## TL;DR

**État actuel:** Aucune base de données persistante dans le MVP actuel. Le bot fonctionne sans DB (pas de mémoire conversationnelle). Ce document propose un schéma cible minimal pour futures évolutions (conversations, messages, sessions, audit).

---

## Ce qui est vrai aujourd'hui

### État Actuel: Pas de Base de Données

**Constat:**
- Aucune base de données configurée dans le repo
- Aucune migration (Alembic, Flyway, etc.)
- Aucune connexion DB dans le code (`services/ganopa-bot/app/main.py`)
- Pas de `docker-compose.yml` avec DB
- Pas de variables d'environnement DB (`DATABASE_URL`, etc.)

**Impact:**
- ✅ MVP fonctionne sans DB (pas de mémoire conversationnelle)
- ⚠️ Pas d'historique des conversations
- ⚠️ Pas de contexte conversationnel (le bot ne se souvient pas des messages précédents)
- ⚠️ Pas d'analytics/métriques persistantes

**Référence:**
- Code: `services/ganopa-bot/app/main.py` → Aucune import DB (SQLAlchemy, psycopg2, etc.)
- Requirements: `services/ganopa-bot/requirements.txt` → Pas de dépendance DB

---

## Comment Lire la DB de ce Repo

### Si une DB est Ajoutée Plus Tard

**Config DB (à prévoir):**
- Variable d'environnement: `DATABASE_URL` (format: `postgresql://user:pass@host:port/dbname`)
- Ou variables séparées: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

**Migrations (à prévoir):**
- Outil recommandé: **Alembic** (pour SQLAlchemy) ou **Flyway** (pour migrations SQL brutes)
- Dossier: `services/ganopa-bot/migrations/` (à créer)
- Commande: `alembic upgrade head` (à ajouter dans Dockerfile ou entrypoint)

**Où chercher:**
- `services/ganopa-bot/app/models.py` (modèles SQLAlchemy, si ajouté)
- `services/ganopa-bot/migrations/versions/` (migrations Alembic, si ajouté)
- `docker-compose.yml` (DB locale pour dev, si ajouté)

---

## Conventions de Nommage

### Tables

- **Format:** `snake_case` (ex: `telegram_conversations`, `telegram_messages`)
- **Préfixe:** `telegram_` pour les tables liées à Telegram
- **Pluriel:** Tables au pluriel (ex: `conversations`, pas `conversation`)

### Colonnes

- **Primary Key:** `id` (type: `BIGSERIAL` ou `UUID`)
- **Timestamps:** `created_at`, `updated_at` (type: `TIMESTAMP WITH TIME ZONE`)
- **Foreign Keys:** `{table}_id` (ex: `conversation_id`, `user_id`)
- **Boolean:** `is_*` (ex: `is_bot`, `is_active`)
- **IDs externes:** `{service}_id` (ex: `telegram_chat_id`, `telegram_update_id`)

### Indexes

- **Primary Key:** Automatique sur `id`
- **Foreign Keys:** Index automatique
- **Recherche fréquente:** Index sur `chat_id`, `created_at`, `update_id`

---

## Schéma Cible Minimal

### Table: `telegram_conversations`

**Description:** Conversations Telegram (une conversation = un chat_id).

**Colonnes:**
- `id` (BIGSERIAL PRIMARY KEY)
- `telegram_chat_id` (BIGINT UNIQUE NOT NULL) - Chat ID Telegram
- `telegram_user_id` (BIGINT) - User ID Telegram (si disponible)
- `is_active` (BOOLEAN DEFAULT true) - Conversation active
- `created_at` (TIMESTAMP WITH TIME ZONE DEFAULT NOW())
- `updated_at` (TIMESTAMP WITH TIME ZONE DEFAULT NOW())

**Indexes:**
- `idx_telegram_conversations_chat_id` sur `telegram_chat_id`
- `idx_telegram_conversations_user_id` sur `telegram_user_id`

**Usage:**
- Suivre les conversations actives
- Lier les messages à une conversation
- Analytics par utilisateur

---

### Table: `telegram_messages`

**Description:** Messages Telegram (in et out).

**Colonnes:**
- `id` (BIGSERIAL PRIMARY KEY)
- `conversation_id` (BIGINT REFERENCES telegram_conversations(id))
- `telegram_update_id` (BIGINT UNIQUE) - Update ID Telegram (pour deduplication)
- `telegram_message_id` (BIGINT) - Message ID Telegram
- `direction` (VARCHAR(10) NOT NULL) - 'in' ou 'out'
- `text` (TEXT) - Contenu du message
- `text_length` (INTEGER) - Longueur du texte
- `is_command` (BOOLEAN DEFAULT false) - Est-ce une commande (/start, /help, etc.)
- `command_name` (VARCHAR(50)) - Nom de la commande (si is_command = true)
- `openai_used` (BOOLEAN DEFAULT false) - OpenAI a été utilisé pour générer la réponse
- `openai_model` (VARCHAR(50)) - Modèle OpenAI utilisé (si openai_used = true)
- `openai_tokens_used` (INTEGER) - Tokens OpenAI utilisés
- `openai_latency_ms` (INTEGER) - Latence OpenAI en millisecondes
- `error_type` (VARCHAR(50)) - Type d'erreur (si erreur)
- `error_message` (TEXT) - Message d'erreur (si erreur)
- `created_at` (TIMESTAMP WITH TIME ZONE DEFAULT NOW())

**Indexes:**
- `idx_telegram_messages_conversation_id` sur `conversation_id`
- `idx_telegram_messages_update_id` sur `telegram_update_id`
- `idx_telegram_messages_created_at` sur `created_at`
- `idx_telegram_messages_direction` sur `direction`

**Usage:**
- Historique des messages
- Analytics (tokens utilisés, latence, erreurs)
- Debug (retrouver un message spécifique)

---

### Table: `telegram_sessions` (Optionnel)

**Description:** Sessions/contexte conversationnel (pour mémoire conversationnelle future).

**Colonnes:**
- `id` (BIGSERIAL PRIMARY KEY)
- `conversation_id` (BIGINT REFERENCES telegram_conversations(id))
- `session_key` (VARCHAR(255) UNIQUE) - Clé de session (ex: "chat_123456")
- `context` (JSONB) - Contexte conversationnel (messages récents, métadonnées)
- `metadata` (JSONB) - Métadonnées additionnelles
- `expires_at` (TIMESTAMP WITH TIME ZONE) - Expiration de la session
- `created_at` (TIMESTAMP WITH TIME ZONE DEFAULT NOW())
- `updated_at` (TIMESTAMP WITH TIME ZONE DEFAULT NOW())

**Indexes:**
- `idx_telegram_sessions_conversation_id` sur `conversation_id`
- `idx_telegram_sessions_session_key` sur `session_key`
- `idx_telegram_sessions_expires_at` sur `expires_at`

**Usage:**
- Mémoire conversationnelle (contexte des messages précédents)
- Sessions temporaires (TTL configurable)

---

### Table: `audit_logs` (Optionnel)

**Description:** Logs d'audit pour traçabilité.

**Colonnes:**
- `id` (BIGSERIAL PRIMARY KEY)
- `event_type` (VARCHAR(50) NOT NULL) - Type d'événement (ex: 'webhook_received', 'openai_called')
- `correlation_id` (VARCHAR(50)) - Correlation ID
- `update_id` (BIGINT) - Update ID Telegram
- `chat_id` (BIGINT) - Chat ID Telegram
- `metadata` (JSONB) - Métadonnées de l'événement
- `created_at` (TIMESTAMP WITH TIME ZONE DEFAULT NOW())

**Indexes:**
- `idx_audit_logs_event_type` sur `event_type`
- `idx_audit_logs_correlation_id` sur `correlation_id`
- `idx_audit_logs_created_at` sur `created_at`

**Usage:**
- Traçabilité complète des événements
- Debug avancé
- Analytics

---

## Diagramme ERD (Mermaid)

```mermaid
erDiagram
    telegram_conversations ||--o{ telegram_messages : "has"
    telegram_conversations ||--o| telegram_sessions : "has"
    
    telegram_conversations {
        bigserial id PK
        bigint telegram_chat_id UK
        bigint telegram_user_id
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    
    telegram_messages {
        bigserial id PK
        bigint conversation_id FK
        bigint telegram_update_id UK
        bigint telegram_message_id
        varchar direction
        text text
        integer text_length
        boolean is_command
        varchar command_name
        boolean openai_used
        varchar openai_model
        integer openai_tokens_used
        integer openai_latency_ms
        varchar error_type
        text error_message
        timestamp created_at
    }
    
    telegram_sessions {
        bigserial id PK
        bigint conversation_id FK
        varchar session_key UK
        jsonb context
        jsonb metadata
        timestamp expires_at
        timestamp created_at
        timestamp updated_at
    }
    
    audit_logs {
        bigserial id PK
        varchar event_type
        varchar correlation_id
        bigint update_id
        bigint chat_id
        jsonb metadata
        timestamp created_at
    }
```

---

## À Compléter

### Quand une DB sera Ajoutée

1. **Choisir le SGBD:**
   - PostgreSQL (recommandé) ou MySQL/MariaDB
   - Configurer dans ECS (RDS ou container)

2. **Ajouter les dépendances:**
   - `sqlalchemy` (ORM)
   - `alembic` (migrations)
   - `psycopg2-binary` (driver PostgreSQL) ou `pymysql` (driver MySQL)

3. **Créer les modèles:**
   - `services/ganopa-bot/app/models.py` (modèles SQLAlchemy)

4. **Créer les migrations:**
   - `services/ganopa-bot/migrations/versions/` (migrations Alembic)

5. **Mettre à jour le code:**
   - Connexion DB dans `main.py`
   - Persister les messages dans `process_telegram_update()`

6. **Mettre à jour ce document:**
   - Remplacer "À compléter" par les valeurs réelles
   - Ajouter les schémas réels

---

## À vérifier quand ça casse

### Une DB est ajoutée mais ce document n'est pas à jour

1. Vérifier les migrations Alembic (`services/ganopa-bot/migrations/versions/`)
2. Vérifier les modèles SQLAlchemy (`services/ganopa-bot/app/models.py`)
3. Mettre à jour ce document avec le schéma réel
4. Mettre à jour `docs/DB_QUERIES.md` avec les requêtes réelles

---

**Dernière mise à jour:** 2025-12-29  
**Status:** Schéma cible proposé, DB non implémentée

