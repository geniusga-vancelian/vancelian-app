# Requêtes Base de Données - Vancelian App

## TL;DR

Requêtes SQL prêtes à copier-coller pour debug, analytics, et maintenance. Format: PostgreSQL (recommandé). À adapter si autre SGBD.

---

## Ce qui est vrai aujourd'hui

### État Actuel: Pas de Base de Données

**Constat:**
- Aucune DB configurée → Ces requêtes sont **proposées pour le futur**
- À utiliser quand une DB sera ajoutée (voir `docs/DB_SCHEMA.md`)

**Alternative Actuelle:**
- Logs CloudWatch pour debug et analytics
- Requêtes CloudWatch Logs Insights (voir section "Alternative CloudWatch")

---

## Requêtes Proposées (Quand DB Sera Ajoutée)

### Lister les 50 Derniers Messages d'un Chat ID

**Usage:** Debug d'une conversation spécifique.

```sql
SELECT
    m.id,
    m.direction,
    m.text,
    m.text_length,
    m.is_command,
    m.command_name,
    m.openai_used,
    m.openai_tokens_used,
    m.openai_latency_ms,
    m.error_type,
    m.created_at
FROM telegram_messages m
JOIN telegram_conversations c ON m.conversation_id = c.id
WHERE c.telegram_chat_id = 123456789  -- Remplacer par le chat_id réel
ORDER BY m.created_at DESC
LIMIT 50;
```

**Variante: Messages d'une période:**
```sql
SELECT
    m.id,
    m.direction,
    m.text,
    m.created_at
FROM telegram_messages m
JOIN telegram_conversations c ON m.conversation_id = c.id
WHERE c.telegram_chat_id = 123456789
  AND m.created_at >= NOW() - INTERVAL '24 hours'
ORDER BY m.created_at DESC;
```

---

### Compter les Messages par Jour

**Usage:** Analytics de volume.

```sql
SELECT
    DATE(m.created_at) AS date,
    COUNT(*) AS total_messages,
    COUNT(*) FILTER (WHERE m.direction = 'in') AS messages_in,
    COUNT(*) FILTER (WHERE m.direction = 'out') AS messages_out,
    COUNT(*) FILTER (WHERE m.is_command = true) AS commands,
    COUNT(*) FILTER (WHERE m.openai_used = true) AS openai_calls
FROM telegram_messages m
WHERE m.created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(m.created_at)
ORDER BY date DESC;
```

**Variante: Par heure (dernières 24h):**
```sql
SELECT
    DATE_TRUNC('hour', m.created_at) AS hour,
    COUNT(*) AS total_messages
FROM telegram_messages m
WHERE m.created_at >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', m.created_at)
ORDER BY hour DESC;
```

---

### Retrouver Erreurs OpenAI

**Usage:** Debug des erreurs OpenAI.

```sql
SELECT
    m.id,
    m.conversation_id,
    c.telegram_chat_id,
    m.text,
    m.error_type,
    m.error_message,
    m.openai_latency_ms,
    m.created_at
FROM telegram_messages m
JOIN telegram_conversations c ON m.conversation_id = c.id
WHERE m.error_type IS NOT NULL
  AND m.created_at >= NOW() - INTERVAL '7 days'
ORDER BY m.created_at DESC
LIMIT 100;
```

**Variante: Grouper par type d'erreur:**
```sql
SELECT
    m.error_type,
    COUNT(*) AS count,
    AVG(m.openai_latency_ms) AS avg_latency_ms
FROM telegram_messages m
WHERE m.error_type IS NOT NULL
  AND m.created_at >= NOW() - INTERVAL '7 days'
GROUP BY m.error_type
ORDER BY count DESC;
```

---

### Retrouver Conversations Actives

**Usage:** Identifier les conversations récentes.

```sql
SELECT
    c.id,
    c.telegram_chat_id,
    c.telegram_user_id,
    c.is_active,
    COUNT(m.id) AS message_count,
    MAX(m.created_at) AS last_message_at
FROM telegram_conversations c
LEFT JOIN telegram_messages m ON m.conversation_id = c.id
WHERE c.is_active = true
GROUP BY c.id, c.telegram_chat_id, c.telegram_user_id, c.is_active
HAVING MAX(m.created_at) >= NOW() - INTERVAL '7 days'
ORDER BY last_message_at DESC;
```

**Variante: Conversations avec le plus de messages:**
```sql
SELECT
    c.telegram_chat_id,
    COUNT(m.id) AS message_count,
    MAX(m.created_at) AS last_message_at
FROM telegram_conversations c
JOIN telegram_messages m ON m.conversation_id = c.id
GROUP BY c.telegram_chat_id
ORDER BY message_count DESC
LIMIT 20;
```

---

### Vérifier Latence OpenAI

**Usage:** Analytics de performance OpenAI.

```sql
SELECT
    DATE(m.created_at) AS date,
    COUNT(*) AS total_calls,
    AVG(m.openai_latency_ms) AS avg_latency_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY m.openai_latency_ms) AS median_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY m.openai_latency_ms) AS p95_latency_ms,
    MAX(m.openai_latency_ms) AS max_latency_ms,
    SUM(m.openai_tokens_used) AS total_tokens
FROM telegram_messages m
WHERE m.openai_used = true
  AND m.created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(m.created_at)
ORDER BY date DESC;
```

**Variante: Latence par modèle:**
```sql
SELECT
    m.openai_model,
    COUNT(*) AS total_calls,
    AVG(m.openai_latency_ms) AS avg_latency_ms,
    AVG(m.openai_tokens_used) AS avg_tokens
FROM telegram_messages m
WHERE m.openai_used = true
  AND m.created_at >= NOW() - INTERVAL '7 days'
GROUP BY m.openai_model
ORDER BY total_calls DESC;
```

---

### Retrouver Messages par Commande

**Usage:** Analytics des commandes utilisées.

```sql
SELECT
    m.command_name,
    COUNT(*) AS usage_count,
    MIN(m.created_at) AS first_used,
    MAX(m.created_at) AS last_used
FROM telegram_messages m
WHERE m.is_command = true
  AND m.command_name IS NOT NULL
GROUP BY m.command_name
ORDER BY usage_count DESC;
```

---

### Retrouver Duplications (Update ID)

**Usage:** Vérifier la deduplication.

```sql
SELECT
    m.telegram_update_id,
    COUNT(*) AS duplicate_count,
    MIN(m.created_at) AS first_seen,
    MAX(m.created_at) AS last_seen
FROM telegram_messages m
WHERE m.telegram_update_id IS NOT NULL
GROUP BY m.telegram_update_id
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

**Note:** Si cette requête retourne des résultats, la deduplication ne fonctionne pas correctement.

---

## Alternative CloudWatch (Actuel)

### Requêtes CloudWatch Logs Insights

**Lister les 50 derniers messages d'un chat_id:**
```
fields @timestamp, correlation_id, chat_id, text_preview, reply_preview
| filter chat_id = 123456789
| sort @timestamp desc
| limit 50
```

**Compter les messages par jour:**
```
fields @timestamp
| stats count() by bin(1d)
| sort @timestamp desc
```

**Retrouver erreurs OpenAI:**
```
fields @timestamp, correlation_id, chat_id, error, error_type
| filter event_type = "openai_error"
| sort @timestamp desc
| limit 100
```

**Vérifier latence OpenAI:**
```
fields @timestamp, latency_ms, tokens_used
| filter event_type = "openai_ok"
| stats avg(latency_ms) as avg_latency, avg(tokens_used) as avg_tokens by bin(1d)
| sort @timestamp desc
```

---

## À Compléter

### Quand une DB sera Ajoutée

1. **Tester les requêtes:**
   - Adapter selon le SGBD réel (PostgreSQL, MySQL, etc.)
   - Vérifier les noms de tables/colonnes réels

2. **Ajouter des requêtes spécifiques:**
   - Requêtes de maintenance (nettoyage, index, etc.)
   - Requêtes d'analytics avancées

3. **Mettre à jour ce document:**
   - Remplacer "À compléter" par les requêtes testées
   - Ajouter des exemples de résultats

---

## À vérifier quand ça casse

### Une requête ne fonctionne pas

1. Vérifier les noms de tables/colonnes (voir `docs/DB_SCHEMA.md`)
2. Vérifier le SGBD (PostgreSQL vs MySQL syntax)
3. Tester la requête avec `EXPLAIN` pour debug

### Besoin d'une nouvelle requête

1. Ajouter la requête dans ce fichier
2. Documenter l'usage
3. Tester la requête

---

**Dernière mise à jour:** 2025-12-29  
**Status:** Requêtes proposées, DB non implémentée

