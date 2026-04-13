# 🚀 Démarrage Rapide — Après Redémarrage de l'Ordinateur

**Commande unique pour tout démarrer automatiquement.**

---

## ⚡ Commande Unique

```bash
cd vancelian-app/services/arquantix
./scripts/arquantix-start.sh
```

**C'est tout.** Le script fait tout automatiquement.

---

## 🔄 Ce que fait le script

1. ✅ Vérifie que Docker est démarré
2. ✅ Vérifie que `arquantix-db` existe
3. ✅ Démarre `arquantix-db` si nécessaire
4. ✅ Attend que la DB soit healthy
5. ✅ Vérifie que le port est 5443 (pas 5434)
6. ✅ Configure la restart policy si nécessaire
7. ✅ Vérifie les configurations `.env` (ports corrects)
8. ✅ Démarre l'API (FastAPI) si pas déjà démarrée
9. ✅ Démarre le Web (Next.js) si pas déjà démarré
10. ✅ Affiche un résumé avec les URLs et logs

---

## ✅ Résultat Attendu

```
╔══════════════════════════════════════════════════════════════════════════╗
║     DÉMARRAGE TERMINÉ                                                    ║
╚══════════════════════════════════════════════════════════════════════════╝

✅ Tous les services sont démarrés

📋 URLs:
   🌐 Web:  http://localhost:3000
   🔐 Admin: http://localhost:3000/admin/login
   🔌 API:  http://localhost:8000/docs

📝 Logs:
   - Web: tail -f /tmp/arquantix-web.log
   - API: tail -f /tmp/arquantix-api.log
   - DB:  docker logs arquantix-db

🔍 Vérifier le status:
   ./scripts/arquantix-status.sh
```

---

## 🔍 Vérifier que tout fonctionne

Après le démarrage, vérifiez le status:

```bash
./scripts/arquantix-status.sh
```

**Résultat attendu:**
```
DB:   running=true | health=healthy | port=5443
API:  http://localhost:8000
Web:  http://localhost:3000
```

---

## 🐛 Si quelque chose ne fonctionne pas

### Erreur: "Docker n'est pas démarré"

**Solution:** Démarrer Docker Desktop manuellement, puis relancer le script.

---

### Erreur: "Container 'arquantix-db' n'existe pas"

**Solution:** Le container doit être créé. Vérifiez s'il existe:
```bash
docker ps -a | grep arquantix-db
```

Si absent, créer le container selon la documentation.

---

### Erreur: "DB n'est pas healthy"

**Solution:** Vérifier les logs:
```bash
docker logs arquantix-db --tail 50
```

Attendre quelques secondes et relancer le script.

---

### Erreur: "Mauvais port DB (5434 au lieu de 5443)"

**Solution:** Vous pointez vers `zitadel-db`. Vérifier quel container écoute sur 5443:
```bash
docker ps | grep 5443
```

---

### API ou Web ne démarrent pas

**Vérifier les logs:**
```bash
# API
tail -50 /tmp/arquantix-api.log

# Web
tail -50 /tmp/arquantix-web.log
```

**Redémarrer manuellement si nécessaire:**
```bash
# API
cd services/arquantix/api
python3 -m uvicorn main:app --reload --port 8000

# Web
cd services/arquantix/web
npm run dev
```

---

## 📋 Workflow Complet

1. **Redémarrer l'ordinateur**
2. **Ouvrir un terminal**
3. **Exécuter:**
   ```bash
   cd vancelian-app/services/arquantix
   ./scripts/arquantix-start.sh
   ```
4. **Vérifier le status:**
   ```bash
   ./scripts/arquantix-status.sh
   ```
5. **Si tout est ✅ → Commencer à travailler**

---

## 🎯 Alias Pratique (Optionnel)

Ajouter dans `~/.zshrc` ou `~/.bashrc`:

```bash
alias arquantix-start='cd ~/Library/CloudStorage/OneDrive-Vancelian/Documents/vancelian-app/services/arquantix && ./scripts/arquantix-start.sh'
alias arquantix-status='cd ~/Library/CloudStorage/OneDrive-Vancelian/Documents/vancelian-app/services/arquantix && ./scripts/arquantix-status.sh'
```

Puis utiliser simplement:
```bash
arquantix-start
arquantix-status
```

---

**Dernière mise à jour:** 2026-01-08





