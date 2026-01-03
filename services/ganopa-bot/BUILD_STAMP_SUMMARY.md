# Build Stamp & Signature Test - Résumé des Modifications

## ✅ Modifications Effectuées

### 1. `services/ganopa-bot/app/main.py`

**Ajouts:**
- ✅ `BOT_BUILD_ID` généré au démarrage (format: `build-YYYYMMDD-HHMMSS`)
- ✅ Log `ganopa_bot_started` enrichi avec:
  - `bot_build_id`
  - `openai_model`
  - `has_openai_key` (bool)
  - `has_webhook_secret` (bool)
  - `signature_test_mode` (bool)
- ✅ Mode signature test dans `process_telegram_update()`:
  - Si `BOT_SIGNATURE_TEST=1` → répond: `✅ VERSION-TEST-123 | <BOT_BUILD_ID>`
  - Sinon → appelle `call_openai()` normalement
- ✅ Logs améliorés:
  - `openai_request_start` (avant appel OpenAI)
  - `openai_request_done` (après succès, avec `latency_ms`, `reply_preview`)
  - `openai_request_error` (en cas d'erreur, avec `latency_ms`)
  - `signature_test_response` (si mode test activé)
  - `telegram_send_done` (remplace `telegram_send_success`)
  - `telegram_send_failed_http` (déjà existant, amélioré)

### 2. `services/ganopa-bot/app/config.py`

**Ajouts:**
- ✅ Fonction `getenv_bool()` pour lire les variables booléennes
- ✅ Variable `BOT_SIGNATURE_TEST` (default: `False`)
- ✅ `OPENAI_API_KEY` et `OPENAI_MODEL` déjà présents (vérifiés)

---

## 🎯 Comment Utiliser

### Mode Normal (Production)

Le bot fonctionne normalement avec OpenAI. Le `BOT_BUILD_ID` apparaît dans les logs au démarrage.

### Mode Signature Test (Vérification)

1. **Activer dans ECS Task Definition:**
   - Ajouter variable d'environnement: `BOT_SIGNATURE_TEST=1`
   - Redémarrer le service

2. **Tester:**
   - Envoyer un message Telegram
   - **Attendu:** `✅ VERSION-TEST-123 | build-20250128-143022`

3. **Vérifier dans CloudWatch:**
   - Chercher `signature_test_response` avec `bot_build_id`

4. **Désactiver après test:**
   - Retirer `BOT_SIGNATURE_TEST` ou mettre `BOT_SIGNATURE_TEST=0`
   - Redémarrer le service

---

## 📊 Logs à Surveiller

### Au Démarrage
```
[INFO] ganopa-bot: ganopa_bot_started {
  "service": "ganopa-bot",
  "bot_build_id": "build-20250128-143022",
  "openai_model": "gpt-4o-mini",
  "has_openai_key": true,
  "has_webhook_secret": false,
  "signature_test_mode": false
}
```

### Mode Signature Test Activé
```
[INFO] ganopa-bot: signature_test_response {
  "update_id": 123456,
  "chat_id": 789012,
  "bot_build_id": "build-20250128-143022"
}
```

### Mode Normal (OpenAI)
```
[INFO] ganopa-bot: openai_request_start {
  "update_id": 123456,
  "chat_id": 789012,
  "text_preview": "Bonjour"
}

[INFO] ganopa-bot: openai_request_done {
  "update_id": 123456,
  "chat_id": 789012,
  "response_len": 45,
  "reply_preview": "Bonjour ! Comment puis-je vous aider ?",
  "latency_ms": 1250
}

[INFO] ganopa-bot: telegram_send_done {
  "update_id": 123456,
  "chat_id": 789012
}
```

---

## 🔍 Preuve de Version

### Méthode 1: Logs CloudWatch

```bash
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --since 1h \
  --filter-pattern "ganopa_bot_started" \
  --format short
```

Chercher `bot_build_id` dans les logs.

### Méthode 2: Signature Test

1. Activer `BOT_SIGNATURE_TEST=1`
2. Envoyer message Telegram
3. Vérifier réponse: `✅ VERSION-TEST-123 | build-YYYYMMDD-HHMMSS`

### Méthode 3: Image ECR vs Git SHA

```bash
# Image déployée
IMAGE_URI=$(aws ecs describe-tasks ... --query "tasks[0].containers[?name=='ganopa-bot'].image" --output text)
IMAGE_TAG=$(echo $IMAGE_URI | cut -d: -f2)

# Commit Git
git rev-parse HEAD

# Comparer
echo "Image tag: $IMAGE_TAG"
echo "Git SHA: $(git rev-parse HEAD)"
```

Si différents → le déploiement n'a pas mis à jour l'image.

---

## 🚨 Diagnostic: Pourquoi "✅ Reçu:" au lieu de réponse IA?

### Si vous voyez encore "✅ Reçu:"

**Causes possibles:**

1. **Ancienne image déployée**
   - Vérifier: `IMAGE_URI` vs `GITHUB_SHA`
   - Solution: Déployer via GitHub Actions

2. **Mauvais service ECS**
   - Vérifier: Le service `ganopa-dev-bot-svc` existe et est actif
   - Solution: Vérifier le nom exact du service

3. **Code non déployé**
   - Vérifier: Le workflow GitHub Actions a-t-il tourné?
   - Solution: Déclencher manuellement le workflow

4. **Service non redémarré**
   - Vérifier: Le service ECS a-t-il été mis à jour?
   - Solution: Forcer un nouveau déploiement

### Si vous ne voyez pas `ganopa_bot_started`

**Causes possibles:**

1. **Service ne démarre pas**
   - Vérifier: Logs ECS pour erreurs (ImportError, SyntaxError)
   - Solution: Vérifier les variables d'environnement

2. **Mauvais log group**
   - Vérifier: Le nom exact du log group CloudWatch
   - Solution: Lister tous les log groups ECS

---

## 📝 Prochaines Étapes

1. **Commit les modifications:**
   ```bash
   git add services/ganopa-bot/app/main.py services/ganopa-bot/app/config.py
   git commit -m "feat: add build stamp and signature test mode for deployment verification"
   git push origin main
   ```

2. **Déployer via GitHub Actions:**
   - Workflow: "Deploy Ganopa Bot (ECS Fargate)"
   - Environnement: `dev`

3. **Vérifier le déploiement:**
   - Voir `VERIFICATION_COMMANDS.md` pour les commandes exactes

4. **Tester:**
   - Activer `BOT_SIGNATURE_TEST=1` temporairement
   - Envoyer message Telegram
   - Vérifier réponse: `✅ VERSION-TEST-123 | build-...`
   - Désactiver le mode test

---

## 🎁 Bonus: Endpoint /version (Optionnel)

Si vous voulez une preuve encore plus directe, on peut ajouter:

```python
@app.get("/version")
def version():
    return {
        "service": "ganopa-bot",
        "bot_build_id": BOT_BUILD_ID,
        "openai_model": OPENAI_MODEL,
        "signature_test_mode": BOT_SIGNATURE_TEST,
    }
```

Puis tester: `curl https://api.maisonganopa.com/version`

---

## ✅ Checklist Finale

- [ ] Code modifié et testé localement
- [ ] Commit créé
- [ ] Push vers GitHub
- [ ] Workflow GitHub Actions déclenché
- [ ] Service ECS déployé
- [ ] Log `ganopa_bot_started` visible dans CloudWatch
- [ ] `BOT_BUILD_ID` présent dans les logs
- [ ] Test signature mode: réponse `✅ VERSION-TEST-123 | build-...`
- [ ] Mode normal: réponse IA fonctionne
- [ ] Image ECR correspond au GITHUB_SHA

---

**Résultat:** Vous pouvez maintenant prouver à 100% quelle version du code tourne réellement dans ECS.


