# Fix: Workflows de Déploiement Automatique

## Problème Résolu

Avant, chaque push vers `main` déclenchait **toujours** le workflow "Deploy API (dev)", même si seul le code de Ganopa Bot changeait. Cela causait :
- Déploiement vers le mauvais service (`vancelian-dev-api-svc` au lieu de `ganopa-dev-bot-svc`)
- Le bot Ganopa n'était jamais mis à jour automatiquement
- Nécessité de déclencher manuellement "Deploy Ganopa Bot"

## Solution Implémentée

### 1. `deploy-dev.yml` (API principale)
- ✅ Ajout de `paths-ignore` pour ignorer les changements dans `services/ganopa-bot/**`
- ✅ Ne se déclenche plus si seul Ganopa Bot change
- ✅ Continue de se déclencher pour tous les autres changements

### 2. `deploy-ganopa-bot.yml` (Bot Ganopa)
- ✅ Ajout de déclenchement automatique sur `push` vers `main`
- ✅ Utilise `paths` pour ne se déclencher que si `services/ganopa-bot/**` change
- ✅ Déploie automatiquement vers `dev` en mode automatique
- ✅ Garde la possibilité de choisir l'environnement en mode manuel (`workflow_dispatch`)

## Comportement Maintenant

### Scénario 1: Modification de Ganopa Bot
```bash
git commit -m "fix: ganopa bot" services/ganopa-bot/app/main.py
git push origin main
```
→ **Seul** "Deploy Ganopa Bot" se déclenche automatiquement vers `dev`

### Scénario 2: Modification de l'API principale
```bash
git commit -m "fix: api" app/main.py
git push origin main
```
→ **Seul** "Deploy API (dev)" se déclenche

### Scénario 3: Modification des deux
```bash
git commit -m "fix: both" services/ganopa-bot/app/main.py app/main.py
git push origin main
```
→ **Les deux** workflows se déclenchent

### Scénario 4: Déploiement manuel
- Via GitHub Actions UI, on peut toujours choisir l'environnement (dev/staging/prod)
- Le mode manuel fonctionne comme avant

## Fichiers Modifiés

1. `.github/workflows/deploy-dev.yml`
   - Ajout de `paths-ignore` pour exclure `services/ganopa-bot/**`

2. `.github/workflows/deploy-ganopa-bot.yml`
   - Ajout de `push` avec `paths` pour déclenchement automatique
   - Modification pour utiliser `dev` par défaut en mode automatique

## Tests à Faire

1. ✅ Modifier un fichier dans `services/ganopa-bot/` et pousser
   - Vérifier que seul "Deploy Ganopa Bot" se déclenche
   
2. ✅ Modifier un fichier ailleurs (ex: `app/main.py`) et pousser
   - Vérifier que seul "Deploy API (dev)" se déclenche

3. ✅ Déclencher manuellement "Deploy Ganopa Bot" avec environnement `staging`
   - Vérifier que ça déploie vers staging

