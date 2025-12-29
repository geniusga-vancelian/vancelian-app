# 🧪 Tests Manuels - Ganopa Bot

## Scénarios de Test Telegram

### Prérequis
- Bot Telegram configuré et actif
- Webhook configuré vers `https://api.maisonganopa.com/telegram/webhook`
- Variables d'environnement configurées (OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, WEBHOOK_SECRET)

---

## Scénario 1: Commande /start

**Action:**
```
Envoyer: /start
```

**Résultat attendu:**
- Message d'accueil avec version
- Liste des commandes disponibles
- Format: "👋 Bienvenue sur Ganopa !..."

**Logs CloudWatch à vérifier:**
- `webhook_received`
- `secret_ok`
- `update_parsed`
- `message_extracted`
- `command_start`
- `command_handled` (avec `command: "/start"`)
- `telegram_sent`

---

## Scénario 2: Commande /help

**Action:**
```
Envoyer: /help
```

**Résultat attendu:**
- Message d'aide avec toutes les commandes
- Exemples d'usage
- Format: "📚 Aide - Ganopa Bot..."

**Logs CloudWatch à vérifier:**
- `command_help`
- `command_handled` (avec `command: "/help"`)
- `telegram_sent`

---

## Scénario 3: Commande /status

**Action:**
```
Envoyer: /status
```

**Résultat attendu:**
- État du service
- Version, Build ID, Modèle IA
- Format: "📊 État du Service..."

**Logs CloudWatch à vérifier:**
- `command_status`
- `command_handled` (avec `command: "/status"`)
- `telegram_sent`

---

## Scénario 4: Question Simple (OpenAI)

**Action:**
```
Envoyer: "Qu'est-ce qu'un paiement instantané ?"
```

**Résultat attendu:**
- Réponse IA générée par OpenAI
- Prefix "🤖" présent
- Réponse en français
- Réponse concise (< 200 mots)

**Logs CloudWatch à vérifier:**
- `message_extracted`
- `openai_called` (avec `text_len`, `text_preview`)
- `openai_ok` (avec `response_len`, `tokens_used`, `latency_ms`)
- `telegram_sent`

---

## Scénario 5: Question Complexe (OpenAI)

**Action:**
```
Envoyer: "Explique-moi les différences entre un compte courant et un compte épargne"
```

**Résultat attendu:**
- Réponse IA détaillée
- Prefix "🤖" présent
- Réponse structurée et claire

**Logs CloudWatch à vérifier:**
- `openai_called`
- `openai_ok` (avec `tokens_used` > 0)
- `telegram_sent`

---

## Scénario 6: Message Vide (Guard)

**Action:**
```
Envoyer: (message vide ou seulement des espaces)
```

**Résultat attendu:**
- Aucune réponse (message ignoré)

**Logs CloudWatch à vérifier:**
- `update_ignored_empty`
- Pas de `openai_called`
- Pas de `telegram_sent`

---

## Scénario 7: Message de Bot (Anti-Loop)

**Action:**
```
Un autre bot envoie un message au bot Ganopa
```

**Résultat attendu:**
- Aucune réponse (message ignoré)

**Logs CloudWatch à vérifier:**
- `update_ignored_bot` (avec `user_id`)
- Pas de `openai_called`
- Pas de `telegram_sent`

---

## Scénario 8: Message Très Long (Troncature)

**Action:**
```
Envoyer une question qui génère une réponse très longue (> 3500 chars)
```

**Résultat attendu:**
- Réponse tronquée à 3500 caractères
- Fin de message: "..."
- Pas d'erreur Telegram

**Logs CloudWatch à vérifier:**
- `openai_ok`
- `message_truncated` (avec `original_length` et `truncated_length`)
- `telegram_sent`

---

## Scénario 9: Update Dupliqué (Deduplication)

**Action:**
```
Envoyer le même message deux fois rapidement (même update_id)
```

**Résultat attendu:**
- Première fois: Réponse normale
- Deuxième fois: Aucune réponse (ignoré)

**Logs CloudWatch à vérifier:**
- Première fois: Logs normaux
- Deuxième fois: `update_duplicate`
- Pas de `openai_called` la deuxième fois

---

## Scénario 10: Erreur OpenAI (Fallback)

**Action:**
```
Simuler une erreur OpenAI (ex: timeout, API key invalide)
```

**Résultat attendu:**
- Message d'erreur utilisateur-friendly
- Format: "⚠️ ..."
- Pas de crash

**Logs CloudWatch à vérifier:**
- `openai_called`
- `openai_error` (avec `error`, `error_type`)
- `telegram_sent` (avec message d'erreur)

---

## Checklist de Validation

### Commandes
- [ ] `/start` retourne message d'accueil avec version
- [ ] `/help` retourne aide complète
- [ ] `/status` retourne état du service

### OpenAI
- [ ] Questions simples génèrent des réponses avec prefix "🤖"
- [ ] Questions complexes génèrent des réponses détaillées
- [ ] Réponses sont en français (ou langue de l'utilisateur)

### Garde-fous
- [ ] Messages vides sont ignorés (`update_ignored_empty`)
- [ ] Messages de bots sont ignorés (`update_ignored_bot`)
- [ ] Messages très longs sont tronqués (`message_truncated`)

### Deduplication
- [ ] Updates dupliqués sont ignorés (`update_duplicate`)

### Logs
- [ ] Tous les logs ont `correlation_id` cohérent
- [ ] Tous les logs ont `update_id` et `chat_id`
- [ ] Aucun secret n'est logué

### Performance
- [ ] Réponses OpenAI < 20s (timeout)
- [ ] Envoi Telegram < 10s (timeout)
- [ ] Réponse webhook immédiate (< 1s)

---

## Commandes de Vérification

### Vérifier les Logs CloudWatch

```bash
# Voir les logs récents
aws logs tail /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --since 10m \
  --format short

# Filtrer par correlation_id
aws logs tail /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --since 10m \
  --format short \
  --filter-pattern "correlation_id"

# Filtrer les commandes
aws logs tail /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --since 10m \
  --format short \
  --filter-pattern "command_"
```

### Vérifier la Version

```bash
curl -s https://api.maisonganopa.com/_meta | jq '.version'
```

---

**Date de création:** 2025-12-29  
**Dernière mise à jour:** 2025-12-29

