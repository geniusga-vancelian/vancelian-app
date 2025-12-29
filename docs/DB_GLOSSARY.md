# Glossaire Base de Données - Vancelian App

## TL;DR

Définitions des termes liés à la base de données et au bot Telegram. Mapping Telegram ↔ DB. Règles de rétention (placeholders).

---

## Ce qui est vrai aujourd'hui

### Définitions

#### user
**Description:** Utilisateur Telegram qui interagit avec le bot.

**Attributs:**
- `telegram_user_id` (BIGINT): ID unique Telegram de l'utilisateur
- `first_name` (VARCHAR): Prénom (depuis Telegram)
- `is_bot` (BOOLEAN): True si c'est un bot (ignoré par le bot Ganopa)

**Source:** `message.from` dans l'update Telegram

**Mapping DB (futur):**
- Table: `telegram_users` (à créer)
- Colonne: `telegram_user_id` (PRIMARY KEY)

---

#### chat_id
**Description:** Identifiant unique d'une conversation Telegram.

**Format:** BIGINT (ex: `123456789`)

**Types de chat:**
- `private`: Conversation privée (1-to-1)
- `group`: Groupe (multi-utilisateurs)
- `supergroup`: Super groupe
- `channel`: Canal

**Source:** `message.chat.id` dans l'update Telegram

**Mapping DB (futur):**
- Table: `telegram_conversations`
- Colonne: `telegram_chat_id` (UNIQUE, NOT NULL)
- Relation: 1 chat_id = 1 conversation

**Usage actuel:**
- Identifiant de conversation dans les logs
- Paramètre pour `sendMessage` Telegram API

---

#### update_id
**Description:** Identifiant unique d'un update Telegram.

**Format:** BIGINT (ex: `123456789`)

**Caractéristiques:**
- Unique par bot
- Croissant (chaque update a un ID supérieur au précédent)
- Utilisé pour deduplication (éviter de traiter le même update deux fois)

**Source:** `update.update_id` dans l'update Telegram

**Mapping DB (futur):**
- Table: `telegram_messages`
- Colonne: `telegram_update_id` (UNIQUE)
- Index: Pour recherche rapide et deduplication

**Usage actuel:**
- Deduplication (cache en mémoire, TTL 5 minutes)
- Correlation ID dans les logs (`correlation_id = f"upd-{update_id}"`)

---

#### message_in
**Description:** Message entrant (de l'utilisateur vers le bot).

**Format:** Texte (TEXT)

**Source:** `message.text` dans l'update Telegram

**Mapping DB (futur):**
- Table: `telegram_messages`
- Colonne: `text` (TEXT)
- Colonne: `direction` = 'in'
- Colonne: `text_length` (INTEGER)

**Usage actuel:**
- Traité directement (pas de persistance)
- Loggé dans CloudWatch avec `text_preview` (50 premiers caractères)

---

#### message_out
**Description:** Message sortant (du bot vers l'utilisateur).

**Format:** Texte (TEXT)

**Source:** Réponse générée par le bot (commande ou OpenAI)

**Mapping DB (futur):**
- Table: `telegram_messages`
- Colonne: `text` (TEXT)
- Colonne: `direction` = 'out'
- Colonne: `text_length` (INTEGER)
- Colonne: `openai_used` (BOOLEAN) - True si généré par OpenAI
- Colonne: `openai_tokens_used` (INTEGER) - Tokens utilisés
- Colonne: `openai_latency_ms` (INTEGER) - Latence en millisecondes

**Usage actuel:**
- Envoyé via Telegram API `sendMessage`
- Loggé dans CloudWatch avec `reply_preview` (50 premiers caractères)

---

#### session
**Description:** Session/contexte conversationnel (pour mémoire conversationnelle future).

**Format:** JSONB (contexte + métadonnées)

**Contenu (proposé):**
```json
{
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "🤖 Bonjour ! Comment puis-je vous aider ?"}
  ],
  "metadata": {
    "language": "fr",
    "topic": "fintech"
  }
}
```

**Mapping DB (futur):**
- Table: `telegram_sessions`
- Colonne: `context` (JSONB)
- Colonne: `session_key` (VARCHAR) - Clé unique (ex: "chat_123456")
- Colonne: `expires_at` (TIMESTAMP) - Expiration de la session

**Usage actuel:**
- ❌ Non implémenté (pas de mémoire conversationnelle)
- 🔄 À implémenter pour contexte multi-tours

---

#### memory
**Description:** Mémoire persistante des conversations (historique long terme).

**Format:** Collection de messages dans `telegram_messages`

**Mapping DB (futur):**
- Table: `telegram_messages` (historique complet)
- Table: `telegram_conversations` (métadonnées de conversation)
- Requête: `SELECT * FROM telegram_messages WHERE conversation_id = ? ORDER BY created_at`

**Usage actuel:**
- ❌ Non implémenté (pas de DB)
- 🔄 À implémenter pour historique et analytics

---

#### tool_call
**Description:** Appel d'outil externe (API banking, calculs, etc.).

**Format:** JSONB (métadonnées de l'appel)

**Contenu (proposé):**
```json
{
  "tool_name": "calculate_interest",
  "parameters": {"principal": 1000, "rate": 0.05, "years": 1},
  "result": {"amount": 1050},
  "latency_ms": 50
}
```

**Mapping DB (futur):**
- Table: `tool_calls` (à créer)
- Colonne: `message_id` (FK vers `telegram_messages`)
- Colonne: `tool_name` (VARCHAR)
- Colonne: `parameters` (JSONB)
- Colonne: `result` (JSONB)
- Colonne: `latency_ms` (INTEGER)

**Usage actuel:**
- ❌ Non implémenté (pas d'outils externes)
- 🔄 À implémenter pour outils futurs

---

## Mapping Telegram ↔ DB

### Update Telegram → DB (Futur)

```
Telegram Update
    │
    ├─→ message.from
    │   └─→ telegram_users (telegram_user_id, first_name, is_bot)
    │
    ├─→ message.chat.id
    │   └─→ telegram_conversations (telegram_chat_id)
    │
    ├─→ update.update_id
    │   └─→ telegram_messages (telegram_update_id, UNIQUE)
    │
    ├─→ message.text (direction = 'in')
    │   └─→ telegram_messages (text, direction, text_length)
    │
    └─→ Réponse bot (direction = 'out')
        └─→ telegram_messages (text, direction, openai_used, openai_tokens_used, openai_latency_ms)
```

### DB → Telegram (Futur)

```
telegram_conversations
    │
    ├─→ telegram_chat_id → Telegram API (sendMessage)
    │
    └─→ telegram_messages (WHERE conversation_id = ?)
        │
        ├─→ direction = 'in' → Messages utilisateur
        │
        └─→ direction = 'out' → Messages bot
```

---

## Règles de Rétention

### Messages (À Configurer)

**Proposé:**
- Messages: Rétention 90 jours (configurable)
- Audit logs: Rétention 30 jours (configurable)
- Sessions: TTL 24 heures (expires_at)

**Implémentation (futur):**
- Job de nettoyage (cron ou Lambda)
- Suppression automatique: `DELETE FROM telegram_messages WHERE created_at < NOW() - INTERVAL '90 days'`

**RGPD:**
- Droit à l'oubli: Suppression sur demande
- Anonymisation: Supprimer `text` mais garder métadonnées pour analytics

---

## À Compléter

### Quand une DB sera Ajoutée

1. **Définir les règles de rétention réelles:**
   - Messages: Combien de temps garder ?
   - Audit logs: Combien de temps garder ?
   - Sessions: TTL configurable ?

2. **Définir les politiques RGPD:**
   - Droit à l'oubli: Comment supprimer les données d'un utilisateur ?
   - Anonymisation: Comment anonymiser les données ?

3. **Mettre à jour ce document:**
   - Remplacer "À compléter" par les valeurs réelles
   - Ajouter les mappings réels

---

## À vérifier quand ça casse

### Un terme n'est pas défini

1. Ajouter la définition dans ce fichier
2. Mettre à jour le mapping Telegram ↔ DB si nécessaire
3. Documenter l'usage dans le code

---

**Dernière mise à jour:** 2025-12-29  
**Status:** Glossaire proposé, DB non implémentée

