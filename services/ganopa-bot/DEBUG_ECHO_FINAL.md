# 🔍 Debug Final: Bot qui échoit

## État Actuel

- ✅ `ganopa_bot_started` présent → Service démarre
- ❌ `openai_request_start` absent → OpenAI jamais appelé
- ❌ Bot échoit toujours

## Diagnostic

Si `openai_request_start` n'apparaît pas, cela signifie que le code n'arrive jamais à la ligne 408 de `main.py`.

### Causes Possibles

1. **Exception dans `process_telegram_update` avant l'appel OpenAI**
   - Chercher `telegram_update_processing_failed` dans les logs
   - Chercher `ERROR` ou `Exception` dans les logs

2. **Le code ne passe pas par `process_telegram_update`**
   - Vérifier `telegram_message_processing` dans les logs
   - Si absent → Exception avant cette ligne

3. **Ancien code tourne encore**
   - Vérifier le `bot_build_id` dans `ganopa_bot_started`
   - Comparer avec le commit déployé

## 🔍 Actions Immédiates

### 1. Vérifier les Logs CloudWatch

**Dans CloudWatch → `/ecs/ganopa-dev-bot-task`:**

Chercher dans les logs récents (après avoir envoyé un message):

#### A) `telegram_update_received`
- **Présent ?** → Le webhook arrive
- **Absent ?** → Le webhook ne pointe pas vers le bon service

#### B) `telegram_message_processing`
- **Présent ?** → Le message est traité
- **Absent ?** → Exception dans `process_telegram_update` avant cette ligne

#### C) `telegram_update_processing_failed`
- **Présent ?** → Voir l'erreur exacte
- **Absent ?** → L'exception n'est pas catchée

#### D) `ERROR` ou `Exception`
- **Présent ?** → Voir l'erreur exacte
- **Absent ?** → Pas d'erreur loggée (problème silencieux)

### 2. Vérifier le Code Déployé

**Dans CloudWatch, chercher `ganopa_bot_started`:**

```json
{
  "bot_build_id": "build-YYYYMMDD-HHMMSS",
  ...
}
```

**Comparer avec:**
- Le timestamp du dernier déploiement
- Le commit déployé (`git log -1`)

**Si le `bot_build_id` est ancien:**
- ❌ L'ancien code tourne encore
- Solution: Forcer un nouveau déploiement

### 3. Test Direct: Vérifier les Erreurs Python

**Dans CloudWatch, filtrer:**
- `ERROR`
- `Exception`
- `Traceback`
- `telegram_update_processing_failed`

**Si vous trouvez une erreur:**
- Partager l'erreur exacte
- Corriger le code
- Redéployer

## 🎯 Question Critique

**Dans les logs CloudWatch, voyez-vous:**

1. `telegram_message_processing` quand vous envoyez un message ?
   - **Oui** → Le code arrive jusqu'à cette ligne, mais pas jusqu'à `openai_request_start`
   - **Non** → Exception avant cette ligne

2. `telegram_update_processing_failed` ?
   - **Oui** → Voir l'erreur exacte
   - **Non** → L'exception n'est pas catchée ou le code ne passe pas par `process_telegram_update`

3. Des erreurs `ERROR` ou `Exception` ?
   - **Oui** → Partager l'erreur
   - **Non** → Problème silencieux (peut-être ancien code)

## 🔧 Solution Temporaire: Mode Signature Test

**Pour prouver que le nouveau code tourne:**

1. ECS → Task Definitions → `ganopa-dev-bot-svc` (dernière révision)
2. Container `ganopa-bot` → Environment variables
3. Ajouter: `BOT_SIGNATURE_TEST` = `1`
4. Enregistrer nouvelle révision
5. Services → `ganopa-dev-bot-svc` → Update service → Sélectionner nouvelle révision
6. Attendre 2-3 minutes
7. Envoyer message Telegram

**Résultat attendu:** `✅ VERSION-TEST-123 | build-YYYYMMDD-HHMMSS`

**Si vous voyez ça:**
- ✅ Le nouveau code tourne
- Le problème est dans la logique OpenAI (probablement exception silencieuse)

**Si vous voyez toujours l'écho:**
- ❌ L'ancien code tourne encore
- Vérifier l'IMAGE URI de la task ECS

