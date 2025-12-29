# Spécifications Fonctionnelles - Vancelian App

## TL;DR

Bot Telegram Ganopa: assistant IA fintech qui répond aux questions des utilisateurs via OpenAI. MVP sans mémoire persistante, avec commandes de base (`/start`, `/help`, `/status`) et protection anti-spam/deduplication.

---

## Ce qui est vrai aujourd'hui

### Périmètre (MVP Ganopa Bot)

**Inclus:**
- Réception webhook Telegram (`POST /telegram/webhook`)
- Génération de réponses via OpenAI (modèle `gpt-4o-mini`)
- Commandes Telegram: `/start`, `/help`, `/status`
- Protection anti-spam (ignore bots, messages vides, deduplication)
- Logs structurés pour observabilité
- Endpoint de vérification de version (`/_meta`)

**Hors périmètre (pour l'instant):**
- Mémoire persistante (conversations, historique)
- Multi-utilisateur avec contexte partagé
- Outils externes (API banking, calculs financiers)
- Authentification utilisateur
- Rate limiting par utilisateur
- Analytics et métriques avancées

---

## Personas

### Gaël (Admin/CTO)
- **Rôle:** Propriétaire du bot, configuration, déploiement
- **Besoins:** Vérifier la version déployée, diagnostiquer les problèmes, monitorer les logs
- **Accès:** AWS Console, GitHub, CloudWatch, endpoint `/_meta`

### Admin (Opérations)
- **Rôle:** Maintenance, monitoring, support
- **Besoins:** Vérifier la santé du service, résoudre les incidents
- **Accès:** AWS Console, CloudWatch, endpoints `/health` et `/_meta`

### User Telegram (Utilisateur Final)
- **Rôle:** Utilisateur du bot via Telegram
- **Besoins:** Poser des questions, obtenir des réponses IA, comprendre les commandes
- **Accès:** Telegram uniquement

---

## User Stories

### US-001: Réception et Traitement de Message Telegram

**En tant que** utilisateur Telegram  
**Je veux** envoyer un message au bot  
**Afin de** recevoir une réponse générée par l'IA

**Critères d'acceptation:**
- ✅ Le webhook Telegram reçoit le message
- ✅ Le bot répond dans les 20 secondes (timeout OpenAI)
- ✅ La réponse commence par "🤖" (preuve IA, pas echo)
- ✅ La réponse est en français (ou langue de l'utilisateur)
- ✅ La réponse est concise (< 200 mots)

**Scénario Gherkin:**
```gherkin
Given un utilisateur Telegram envoie "Qu'est-ce qu'un paiement instantané ?"
When le webhook reçoit le message
Then le bot appelle OpenAI avec le texte
And le bot reçoit une réponse de l'IA
And le bot envoie "🤖 [réponse IA]" à l'utilisateur
And les logs CloudWatch contiennent "openai_ok"
```

---

### US-002: Commandes Telegram

**En tant que** utilisateur Telegram  
**Je veux** utiliser des commandes (`/start`, `/help`, `/status`)  
**Afin de** comprendre le bot et vérifier son état

**Critères d'acceptation:**
- ✅ `/start` retourne un message d'accueil avec version
- ✅ `/help` retourne la liste des commandes et usage
- ✅ `/status` retourne l'état du service (version, modèle, statut)

**Scénario Gherkin:**
```gherkin
Given un utilisateur Telegram envoie "/start"
When le webhook reçoit la commande
Then le bot répond avec message d'accueil
And le message contient la version du bot
And les logs CloudWatch contiennent "command_start"
```

---

### US-003: Gestion des Erreurs OpenAI

**En tant que** utilisateur Telegram  
**Je veux** recevoir un message d'erreur clair  
**Afin de** comprendre pourquoi ma question n'a pas été traitée

**Critères d'acceptation:**
- ✅ Si `OPENAI_API_KEY` manquante → "⚠️ OPENAI_API_KEY manquante (backend config)."
- ✅ Si timeout OpenAI → "⚠️ Délai d'attente dépassé. Veuillez réessayer."
- ✅ Si erreur réseau → "⚠️ Problème de connexion. Veuillez réessayer dans quelques instants."
- ✅ Si erreur API OpenAI → Message d'erreur utilisateur-friendly selon le code HTTP

**Scénario Gherkin:**
```gherkin
Given OpenAI API est indisponible (timeout)
When le bot tente d'appeler OpenAI
Then le bot log "openai_error" avec "error: timeout"
And le bot envoie "⚠️ Délai d'attente dépassé. Veuillez réessayer." à l'utilisateur
```

---

### US-004: Sécurité Webhook Secret Token

**En tant que** admin  
**Je veux** protéger le webhook avec un secret token  
**Afin de** éviter les appels non autorisés

**Critères d'acceptation:**
- ✅ Si `WEBHOOK_SECRET` configuré, le header `X-Telegram-Bot-Api-Secret-Token` est vérifié
- ✅ Si le secret est incorrect → HTTP 401
- ✅ Si le secret est manquant et `WEBHOOK_SECRET` configuré → HTTP 401
- ✅ Si `WEBHOOK_SECRET` non configuré, le webhook accepte tous les appels (mode dev)

**Scénario Gherkin:**
```gherkin
Given WEBHOOK_SECRET="Azerty0334" est configuré
When un webhook arrive sans header X-Telegram-Bot-Api-Secret-Token
Then le bot retourne HTTP 401
And les logs CloudWatch contiennent "secret_ok" avec "secret_ok: false"
```

---

### US-005: Protection Anti-Spam

**En tant que** système  
**Je veux** ignorer les messages de bots et les duplications  
**Afin de** éviter les boucles infinies et les coûts inutiles

**Critères d'acceptation:**
- ✅ Messages de bots (`message.from.is_bot == True`) → ignorés, log `update_ignored_bot`
- ✅ Messages vides (texte vide ou seulement espaces) → ignorés, log `update_ignored_empty`
- ✅ Updates dupliqués (même `update_id` dans les 5 dernières minutes) → ignorés, log `update_duplicate`

**Scénario Gherkin:**
```gherkin
Given un bot Telegram envoie un message au bot Ganopa
When le webhook reçoit le message avec "from.is_bot: true"
Then le bot ignore le message
And les logs CloudWatch contiennent "update_ignored_bot"
And aucun appel OpenAI n'est effectué
```

---

## Scénarios Détaillés

### Scénario 1: Message Telegram → Réponse IA

**Préconditions:**
- Bot actif et déployé
- `OPENAI_API_KEY` configurée
- Webhook Telegram configuré vers `https://api.maisonganopa.com/telegram/webhook`

**Étapes:**
1. Utilisateur envoie "Hello" sur Telegram
2. Telegram POST vers `/telegram/webhook` avec payload JSON
3. FastAPI reçoit le webhook, vérifie le secret, répond `{"ok": true}` immédiatement
4. Background task parse l'update, extrait `chat_id` et `text`
5. Background task appelle OpenAI avec le texte
6. OpenAI retourne une réponse
7. Background task envoie "🤖 [réponse]" à Telegram
8. Utilisateur reçoit la réponse

**Résultat attendu:**
- Réponse reçue dans les 20 secondes
- Réponse commence par "🤖"
- Logs CloudWatch: `webhook_received` → `openai_called` → `openai_ok` → `telegram_sent`

---

### Scénario 2: Erreurs OpenAI → Fallback

**Préconditions:**
- Bot actif et déployé
- OpenAI API indisponible ou erreur

**Variantes:**

**A) Timeout OpenAI:**
- OpenAI ne répond pas dans les 20 secondes
- Bot log `openai_error` avec `error: timeout`
- Bot envoie "⚠️ Délai d'attente dépassé. Veuillez réessayer."

**B) Erreur API Key:**
- `OPENAI_API_KEY` manquante ou invalide
- Bot log `openai_error` avec `error: missing_api_key` ou `status_code: 401`
- Bot envoie "⚠️ OPENAI_API_KEY manquante (backend config)." ou "⚠️ Erreur d'authentification API."

**C) Erreur Réseau:**
- Connexion à OpenAI échoue
- Bot log `openai_error` avec `error: network_error`
- Bot envoie "⚠️ Problème de connexion. Veuillez réessayer dans quelques instants."

---

### Scénario 3: Sécurité Webhook Secret Token

**Préconditions:**
- `WEBHOOK_SECRET=Azerty0334` configuré dans ECS Task Definition

**Variantes:**

**A) Secret Correct:**
- Webhook arrive avec header `X-Telegram-Bot-Api-Secret-Token: Azerty0334`
- Bot vérifie le secret, log `secret_ok` avec `secret_ok: true`
- Bot traite le message normalement

**B) Secret Incorrect:**
- Webhook arrive avec header `X-Telegram-Bot-Api-Secret-Token: wrong`
- Bot vérifie le secret, log `secret_ok` avec `secret_ok: false`
- Bot retourne HTTP 401, ne traite pas le message

**C) Secret Manquant:**
- Webhook arrive sans header `X-Telegram-Bot-Api-Secret-Token`
- Bot vérifie le secret, log `secret_ok` avec `secret_ok: false`
- Bot retourne HTTP 401, ne traite pas le message

---

## Non-Fonctionnel

### Latence

**Objectifs:**
- Réponse webhook immédiate: < 1 seconde (pour satisfaire Telegram)
- Réponse OpenAI: < 20 secondes (timeout configuré)
- Envoi Telegram: < 10 secondes (timeout configuré)

**Mesure:**
- Logs CloudWatch: `latency_ms` dans `openai_ok` et `telegram_sent`

---

### Disponibilité

**Objectifs:**
- Uptime: 99.5% (objectif MVP)
- Health check: `/health` répond 200 OK
- Target Group: Au moins 1 target healthy

**Mesure:**
- CloudWatch Alarms (à configurer)
- Health check ALB → Target Group → ECS tasks

---

### Logs

**Objectifs:**
- Tous les événements sont loggés avec `correlation_id`
- Aucun secret n'est logué (seulement booléens)
- Logs structurés (JSON) dans CloudWatch

**Format:**
- Log group: `/ecs/ganopa-dev-bot-task`
- Events: `webhook_received`, `openai_called`, `openai_ok`, `telegram_sent`, etc.

---

### RGPD Minimal

**Objectifs:**
- Pas de stockage persistant des messages (MVP)
- Logs CloudWatch avec rétention limitée (à configurer)
- Pas de données personnelles dans les logs (seulement `chat_id`, `update_id`)

**À compléter:**
- Politique de rétention des logs CloudWatch
- Politique de suppression des données (si DB ajoutée plus tard)

---

## Hors Périmètre

**Explicitement exclu du MVP:**
- Base de données persistante (conversations, historique)
- Mémoire conversationnelle (le bot ne se souvient pas des messages précédents)
- Multi-utilisateur avec contexte partagé
- Outils externes (API banking, calculs financiers)
- Authentification utilisateur
- Rate limiting par utilisateur
- Analytics et métriques avancées
- Webhook Telegram avec retry automatique
- Support de fichiers/images (seulement texte pour l'instant)

---

## À vérifier quand ça casse

### Un scénario ne fonctionne pas

1. Vérifier les logs CloudWatch pour identifier l'étape qui échoue
2. Vérifier la version déployée (`/_meta`)
3. Vérifier les variables d'environnement (ECS Task Definition)
4. Consulter `docs/RUNBOOK.md` pour la procédure de diagnostic

### Un nouveau besoin fonctionnel apparaît

1. Documenter le besoin dans ce fichier (section "Hors Périmètre" ou nouvelle User Story)
2. Créer un ADR dans `docs/DECISIONS.md` si une décision architecturale est nécessaire
3. Mettre à jour `docs/ARCHITECTURE.md` si l'architecture change

---

**Dernière mise à jour:** 2025-12-29

