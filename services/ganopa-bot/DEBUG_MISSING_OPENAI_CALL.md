# 🔍 Debug: openai_request_start Absent

## Problème

`openai_request_start` est absent dans les logs, ce qui signifie que le code n'arrive jamais à la ligne 408 de `main.py`.

## 🎯 Vérifications Critiques

### 1. Vérifier les Logs Avant l'Appel OpenAI

**Dans CloudWatch → `/ecs/ganopa-dev-bot-task`:**

**Après avoir envoyé un message Telegram, chercher dans l'ordre:**

#### A) `telegram_update_received`
- **Présent ?** → Le webhook arrive au service
- **Absent ?** → Le webhook ne pointe pas vers le bon service

#### B) `telegram_message_processing`
- **Présent ?** → Le code arrive jusqu'à cette ligne (ligne 384)
- **Absent ?** → Exception avant cette ligne (message manquant, chat_id manquant, etc.)

#### C) `signature_test_response`
- **Présent ?** → Le mode signature test est activé (BOT_SIGNATURE_TEST=1)
- **Absent ?** → Mode normal

#### D) `telegram_update_processing_failed`
- **Présent ?** → Exception catchée dans `process_telegram_update_safe`
- **Absent ?** → Pas d'exception catchée

#### E) `ERROR` ou `Exception` ou `Traceback`
- **Présent ?** → Voir l'erreur exacte
- **Absent ?** → Pas d'erreur loggée

### 2. Vérifier le Mode Signature Test

**Si `signature_test_response` est présent:**
- Le mode signature test est activé
- Le bot répond avec `✅ VERSION-TEST-123 | build-...`
- OpenAI n'est jamais appelé (c'est normal en mode test)

**Solution:** Désactiver le mode test dans la Task Definition

### 3. Vérifier les Variables d'Environnement

**Dans AWS Console → ECS → Task Definitions → `ganopa-dev-bot-task:23`:**

**Container `ganopa-bot` → Environment variables:**

- [ ] `BOT_SIGNATURE_TEST` = `0` ou absent (pas `1`)
- [ ] `OPENAI_API_KEY` est présent et non vide
- [ ] `TELEGRAM_BOT_TOKEN` est présent et non vide

**Si `BOT_SIGNATURE_TEST=1`:**
- Le bot est en mode test
- OpenAI n'est jamais appelé
- Solution: Modifier la variable à `0` ou la supprimer

## 🔧 Solutions

### Solution 1: Désactiver le Mode Signature Test

**Si `BOT_SIGNATURE_TEST=1` dans la Task Definition:**

1. **ECS → Task Definitions → `ganopa-dev-bot-task:23`**
2. **Créer une révision** (ou modifier)
3. **Container `ganopa-bot` → Environment variables**
4. **Modifier `BOT_SIGNATURE_TEST`:** `0` ou supprimer la variable
5. **Enregistrer nouvelle révision**
6. **Services → `ganopa-dev-bot-svc` → Update service**
7. **Sélectionner nouvelle révision**
8. **Force new deployment**
9. Attendre stabilisation

### Solution 2: Vérifier les Erreurs dans les Logs

**Si `telegram_update_processing_failed` est présent:**

1. Voir l'erreur exacte dans les logs
2. Corriger le code
3. Redéployer

**Si `telegram_message_processing` est absent:**

1. Chercher `telegram_update_no_message` ou `telegram_message_missing_chat_id`
2. Vérifier le format du webhook Telegram
3. Vérifier que le message contient `text` et `chat.id`

### Solution 3: Vérifier le Code dans l'Image

**Si aucune erreur n'est loggée:**

1. Pull l'image et vérifier le code:
```bash
docker pull 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:fd2c06e053de6f4efed3f6497b700ec91fae2eef
docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:fd2c06e053de6f4efed3f6497b700ec91fae2eef \
  grep -n "openai_request_start" app/main.py
```

2. Vérifier que le code contient bien la logique OpenAI

## 🚨 Questions Critiques

**Répondez à ces questions:**

1. **Voyez-vous `telegram_update_received` dans les logs ?**
   - **Oui** → Le webhook arrive
   - **Non** → Le webhook ne pointe pas vers le bon service

2. **Voyez-vous `telegram_message_processing` dans les logs ?**
   - **Oui** → Le code arrive jusqu'à cette ligne
   - **Non** → Exception avant cette ligne

3. **Voyez-vous `signature_test_response` dans les logs ?**
   - **Oui** → Le mode test est activé (c'est le problème !)
   - **Non** → Mode normal

4. **Voyez-vous `telegram_update_processing_failed` dans les logs ?**
   - **Oui** → Voir l'erreur exacte
   - **Non** → Pas d'exception catchée

5. **Quelle est la valeur de `BOT_SIGNATURE_TEST` dans la Task Definition ?**
   - `1` → Mode test activé (c'est le problème !)
   - `0` ou absent → Mode normal

**Avec ces réponses, je pourrai identifier le problème exact.**

