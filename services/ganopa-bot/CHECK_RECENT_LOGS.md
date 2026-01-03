# Vérification des Logs Récents

## 📊 Commandes pour Voir les Logs les Plus Récents

### Option 1: Via AWS Console (Recommandé)

1. **AWS Console → CloudWatch → Log Groups**
2. **Sélectionner:** `/ecs/ganopa-dev-bot-task` (ou `/aws/ecs/ganopa-dev-bot`)
3. **Filtrer par temps:**
   - Cliquer sur "1h" ou "30m" pour voir les logs récents
   - OU utiliser le calendrier pour sélectionner les dernières heures
4. **Chercher spécifiquement:**
   - `ganopa_bot_started` → Doit apparaître au démarrage
   - `telegram_update_received` → Quand un webhook arrive
   - `openai_request_start` → Quand OpenAI est appelé
   - `ERROR` ou `Exception` → Pour voir les erreurs

### Option 2: Via AWS CLI

```bash
# Voir les logs des 30 dernières minutes
aws logs tail /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --since 30m \
  --format short

# OU pour le log group alternatif
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --since 30m \
  --format short
```

### Option 3: Filtrer par Log Stream Récent

1. **Dans CloudWatch, regarder la colonne "Nom du flux de journaux"**
2. **Identifier le log stream le plus récent** (celui avec les timestamps les plus récents)
3. **Cliquer sur ce log stream** pour voir uniquement ses logs

## 🔍 Ce qu'il faut Chercher

### Logs Normaux (Service Fonctionnel)

1. **Au démarrage:**
   ```
   [INFO] ganopa-bot: ganopa_bot_started {
     "bot_build_id": "build-YYYYMMDD-HHMMSS",
     "openai_model": "gpt-4o-mini",
     "has_openai_key": true,
     ...
   }
   ```

2. **Health checks (toutes les 30s):**
   ```
   INFO: 127.0.0.1:XXXXX - "GET /health HTTP/1.1" 200 OK
   ```

3. **Quand un webhook arrive:**
   ```
   [INFO] ganopa-bot: telegram_update_received {
     "update_id": 123456,
     "has_message": true,
     ...
   }
   ```

4. **Quand OpenAI est appelé:**
   ```
   [INFO] ganopa-bot: openai_request_start {
     "update_id": 123456,
     "chat_id": 789,
     "text_preview": "...",
     ...
   }
   ```

### Logs d'Erreur (Problème)

- `ERROR` → Erreur quelconque
- `Exception` → Exception Python
- `Traceback` → Stack trace complet
- `ImportError` → Module manquant
- `SyntaxError` → Code invalide
- `ModuleNotFoundError` → Module non trouvé

## 🎯 Action Immédiate

**Vérifiez les logs des 30 dernières minutes ou 1 heure:**

1. Dans CloudWatch, sélectionner la plage de temps "30m" ou "1h"
2. Chercher `ganopa_bot_started` dans les logs récents
3. Si présent → Le service démarre correctement
4. Si absent → Le code Python ne démarre pas (chercher les erreurs)

**Partagez ce que vous voyez dans les logs récents !**


