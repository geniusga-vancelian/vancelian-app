# Decisions - Vancelian App

## TL;DR

Décisions architecturales documentées au format ADR (Architecture Decision Record) léger. Format: ADR-XXXX: Titre + Contexte + Décision + Conséquences.

---

## Ce qui est vrai aujourd'hui

### ADR-0001: Webhook Telegram via ALB + ECS (BackgroundTasks)

**Date:** 2025-12-29  
**Status:** ✅ Implémenté

**Contexte:**
- Telegram requiert une réponse HTTP 200 OK dans les 5 secondes
- Le traitement OpenAI peut prendre jusqu'à 20 secondes
- Besoin de scalabilité (ECS Fargate)

**Décision:**
- Utiliser FastAPI `BackgroundTasks` pour traitement asynchrone
- Répondre immédiatement avec `{"ok": true}` au webhook
- Traiter l'update en arrière-plan (parse → OpenAI → sendMessage)

**Conséquences:**
- ✅ Telegram reçoit toujours une réponse rapide
- ✅ Pas de timeout Telegram
- ✅ Scalabilité via ECS (multiple tasks)
- ⚠️ Pas de retry automatique si le background task échoue (mais logs complets)

**Références:**
- Code: `services/ganopa-bot/app/main.py` → `telegram_webhook()` → `background_tasks.add_task()`

---

### ADR-0002: Secrets via ECS Task Definition env vars

**Date:** 2025-12-29  
**Status:** ✅ Implémenté

**Contexte:**
- Besoin de secrets: `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `WEBHOOK_SECRET`
- Pas de AWS Secrets Manager ou Parameter Store configuré
- Simplicité pour MVP

**Décision:**
- Stocker les secrets dans la Task Definition ECS comme variables d'environnement
- Pas de `python-dotenv` en production (seulement `.env` local)
- Logs: seulement booléens (`has_openai_key`, `has_webhook_secret`), jamais les valeurs

**Conséquences:**
- ✅ Simple à configurer
- ✅ Pas de dépendance externe
- ⚠️ Secrets visibles dans la Task Definition (mais ECS est sécurisé)
- 🔄 Migration future possible vers AWS Secrets Manager

**Références:**
- Code: `services/ganopa-bot/app/config.py` → `getenv_required()`, `getenv()`
- ECS: Task Definition → Container Definitions → Environment variables

---

### ADR-0003: Proof-of-deploy via /_meta + prefix 🤖

**Date:** 2025-12-29  
**Status:** ✅ Implémenté

**Contexte:**
- Besoin de prouver que la bonne version est déployée
- Problème récurrent: "le code ne change pas" après déploiement
- Besoin de distinguer réponses IA vs echo

**Décision:**
- Endpoint `/_meta` avec `version` (hash basé sur SERVICE_NAME + BUILD_ID)
- Headers HTTP: `X-Ganopa-Build-Id`, `X-Ganopa-Version`
- Prefix "🤖 " sur toutes les réponses OpenAI (preuve non-echo)

**Conséquences:**
- ✅ Vérification rapide: `curl https://api.maisonganopa.com/_meta | jq .version`
- ✅ Preuve visuelle que l'IA répond (prefix 🤖)
- ✅ Logs structurés avec `version` dans `ganopa_bot_started`

**Références:**
- Code: `services/ganopa-bot/app/main.py` → `VERSION`, `/_meta`, `X-Ganopa-Version` header
- Tests: `curl -s https://api.maisonganopa.com/_meta | jq`

---

### ADR-0004: Deduplication in-memory (5min TTL)

**Date:** 2025-12-29  
**Status:** ✅ Implémenté

**Contexte:**
- Telegram peut envoyer le même update plusieurs fois
- Risque de traiter le même message plusieurs fois (coût OpenAI, spam)

**Décision:**
- Cache en mémoire (`OrderedDict`) avec TTL de 5 minutes
- Clé: `update_id`, Valeur: timestamp
- Nettoyage automatique des entrées expirées
- Limite: 10000 entrées max (supprime les plus anciennes)

**Conséquences:**
- ✅ Évite les duplications
- ✅ Pas de dépendance externe (Redis, etc.)
- ⚠️ Cache perdu au redémarrage (acceptable pour MVP)
- 🔄 Migration future possible vers Redis/DynamoDB si besoin

**Références:**
- Code: `services/ganopa-bot/app/main.py` → `_is_duplicate_update()`, `_update_cache`

---

### ADR-0005: Command System (parse_update + route_command)

**Date:** 2025-12-29  
**Status:** ✅ Implémenté

**Contexte:**
- Besoin de commandes Telegram (`/start`, `/help`, `/status`)
- Code `main.py` devenait trop long
- Besoin de séparation des responsabilités

**Décision:**
- Créer `telegram_handlers.py` avec:
  - `parse_update()` : extraction des données Telegram
  - `route_command()` : routing des commandes
  - `truncate_message()` : troncature des messages longs
- `main.py` reste simple: verify → parse → handler → send

**Conséquences:**
- ✅ Code plus maintenable
- ✅ Facile d'ajouter de nouvelles commandes
- ✅ Tests unitaires possibles sur `telegram_handlers.py`

**Références:**
- Code: `services/ganopa-bot/app/telegram_handlers.py`
- Code: `services/ganopa-bot/app/main.py` → `process_telegram_update()`

---

## Template pour Nouveaux ADR

```markdown
### ADR-XXXX: [Titre Court]

**Date:** YYYY-MM-DD  
**Status:** ✅ Implémenté | 🔄 En cours | ❌ Rejeté

**Contexte:**
- [Pourquoi cette décision était nécessaire]

**Décision:**
- [Qu'est-ce qui a été décidé]

**Conséquences:**
- ✅ [Avantages]
- ⚠️ [Inconvénients / Limitations]
- 🔄 [Évolutions futures possibles]

**Références:**
- Code: `path/to/file.py` → `function_name()`
- Docs: `docs/FILE.md`
```

---

## À vérifier quand ça casse

### Une décision semble obsolète

1. Vérifier la date de l'ADR
2. Vérifier le code actuel (est-ce que l'ADR est toujours respecté ?)
3. Si non, soit:
   - Mettre à jour l'ADR (nouvelle décision)
   - Créer un nouvel ADR qui invalide l'ancien

### Besoin de prendre une nouvelle décision

1. Créer un nouvel ADR avec le template ci-dessus
2. Numéroter séquentiellement (ADR-0006, ADR-0007, etc.)
3. Documenter le contexte, la décision, et les conséquences
4. Ajouter des références vers le code

---

**Dernière mise à jour:** 2025-12-29

