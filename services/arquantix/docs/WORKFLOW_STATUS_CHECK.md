# 🔍 Workflow: Vérification du Status Arquantix

**À utiliser à CHAQUE reprise de travail sur Arquantix.**

---

## 🚀 Commande

```bash
cd vancelian-app/services/arquantix
./scripts/arquantix-status.sh
```

---

## ✅ Résultat Attendu (Tout est OK)

```
==============================
 ARQUANTIX STATUS CHECK
==============================

[DB] Checking container: arquantix-db
DB container found
Running: true
Health:  healthy
Port:    5443
Restart policy: unless-stopped

[API] Checking FastAPI (port 8000)
API: ✅ reachable (http://localhost:8000/docs)

[WEB] Checking Next.js (port 3000)
Web: ✅ reachable (http://localhost:3000)
Admin Login: ✅ reachable (/admin/login)

==============================
 STATUS SUMMARY
==============================
DB:   running=true | health=healthy | port=5443
API:  http://localhost:8000
Web:  http://localhost:3000

If something is ❌, read logs:
- /tmp/arquantix-web.log
- /tmp/arquantix-api.log
- docker logs arquantix-db

==============================
```

**Si vous voyez exactement ça → vous pouvez continuer à travailler.**

---

## ❌ Résultats Problématiques

### Cas 1: DB n'existe pas

```
❌ DB container 'arquantix-db' does NOT exist
STATUS: DB = NOT PRESENT
```

**Action:** Créer le container ou vérifier le nom.

---

### Cas 2: DB arrêtée ou non healthy

```
DB container found
Running: false
Health:  unknown
Port:    5443

❌ DB NOT READY — NO FIX POSSIBLE YET
```

**Action:**
```bash
docker start arquantix-db
# Attendre 10 secondes
./scripts/arquantix-status.sh  # Re-vérifier
```

---

### Cas 3: Mauvais port (5434 au lieu de 5443)

```
DB container found
Running: true
Health:  healthy
Port:    5434

❌ WRONG DB PORT (5434)
Expected: 5443
Likely using wrong database (zitadel-db?)
```

**Action:** Arrêter immédiatement. Vous pointez vers `zitadel-db` au lieu de `arquantix-db`. Corriger la configuration.

---

### Cas 4: API non accessible

```
[API] Checking FastAPI (port 8000)
API: ❌ NOT reachable
```

**Action:**
```bash
# Vérifier que l'API est démarrée
cd services/arquantix/api
python3 -m uvicorn main:app --reload --port 8000

# Vérifier les logs
tail -50 /tmp/arquantix-api.log
```

---

### Cas 5: Web non accessible

```
[WEB] Checking Next.js (port 3000)
Web: ❌ NOT reachable
```

**Action:**
```bash
# Vérifier que Web est démarré
cd services/arquantix/web
npm run dev

# Vérifier les logs
tail -50 /tmp/arquantix-web.log
```

---

## 📋 Règle d'Or

**Si le script affiche autre chose que:**
```
DB:   running=true | health=healthy | port=5443
API:  http://localhost:8000
Web:  http://localhost:3000
```

**→ NE PAS AVANCER. CORRIGER AVANT.**

---

## 🔄 Workflow Complet

1. **Reprendre le travail:**
   ```bash
   cd vancelian-app/services/arquantix
   ```

2. **Vérifier le status:**
   ```bash
   ./scripts/arquantix-status.sh
   ```

3. **Si tout est ✅:**
   - Continuer à travailler

4. **Si quelque chose est ❌:**
   - Lire les logs indiqués
   - Corriger le problème
   - Re-vérifier avec `./scripts/arquantix-status.sh`
   - Répéter jusqu'à ce que tout soit ✅

---

## 💡 Intégration avec Cursor

Avant de proposer **n'importe quelle modification**, Cursor doit:

1. Exécuter `./scripts/arquantix-status.sh`
2. Vérifier que le résultat est exactement:
   ```
   DB:   running=true | health=healthy | port=5443
   API:  http://localhost:8000
   Web:  http://localhost:3000
   ```
3. Si ce n'est pas le cas → **STOP, corriger d'abord**

---

**Dernière mise à jour:** 2026-01-08





