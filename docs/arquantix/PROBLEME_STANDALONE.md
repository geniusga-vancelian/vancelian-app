# Problème Serveur Standalone Next.js

**Date:** 2026-01-03  
**Problème:** Le serveur Next.js démarre mais ne répond pas aux requêtes HTTP

---

## 🔍 Symptômes

- ✅ Service ECS: RUNNING
- ✅ Serveur démarre: "Ready in 390ms" dans les logs
- ❌ Serveur ne répond pas: Timeout sur toutes les requêtes HTTP
- ❌ Health check: UNHEALTHY
- ❌ ALB: 502 Bad Gateway

---

## 🔎 Diagnostic

### Tests Effectués

1. **Test direct depuis IP privée:**
   ```bash
   curl http://172.31.5.199:3000/health
   # Timeout après 3 secondes
   ```

2. **Test depuis ALB:**
   ```bash
   curl http://ALB_DNS/health
   # 502 Bad Gateway
   ```

3. **Logs ECS:**
   ```
   ✓ Starting...
   ✓ Ready in 390ms
   ```
   Le serveur indique qu'il est prêt, mais ne répond pas.

### Configuration Actuelle

**Dockerfile:**
```dockerfile
# Copy standalone build output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

CMD ["node", "server.js"]
```

**next.config.js:**
```javascript
const nextConfig = {
  output: 'standalone',
}
```

---

## 💡 Causes Possibles

### 1. Build Standalone Incomplet

Le build Next.js standalone pourrait ne pas créer correctement `server.js` dans `.next/standalone/`.

**Vérification:**
- Vérifier les logs du build GitHub Actions
- Vérifier que `server.js` existe dans l'image Docker

### 2. Problème de Port/Interface

Le serveur pourrait écouter sur la mauvaise interface ou le mauvais port.

**Vérification:**
- Les variables d'environnement sont correctes:
  - `PORT=3000`
  - `HOSTNAME="0.0.0.0"`

### 3. Problème avec Next.js Standalone

Il pourrait y avoir un bug ou une incompatibilité avec Next.js 14.2.35 en mode standalone.

---

## ✅ Solutions Appliquées

1. **Timeout Health Check Augmenté:**
   - Ancien: 5 secondes
   - Nouveau: 10 secondes

2. **Endpoint /health Créé:**
   - Route API dédiée pour les health checks

---

## 🔄 Solutions à Essayer

### Option 1: Vérifier le Build Localement

```bash
cd services/arquantix/web
npm run build
ls -la .next/standalone/
# Vérifier que server.js existe
```

### Option 2: Tester l'Image Docker Localement

```bash
docker build -t arquantix-test -f services/arquantix/web/Dockerfile services/arquantix/web
docker run -p 3000:3000 arquantix-test
curl http://localhost:3000/health
```

### Option 3: Revenir à `next start`

Si le problème persiste, essayer de revenir à `next start` au lieu de standalone:

```dockerfile
# Au lieu de:
CMD ["node", "server.js"]

# Utiliser:
CMD ["node_modules/.bin/next", "start", "-p", "3000"]
```

**Mais attention:** Cela nécessite de retirer `output: 'standalone'` de `next.config.js`.

### Option 4: Vérifier les Logs du Build

Vérifier les logs GitHub Actions pour voir si le build standalone réussit:
- https://github.com/geniusga-vancelian/vancelian-app/actions

---

## 📊 Prochaines Étapes

1. ⏳ Attendre 1-2 minutes pour que le health check se réévalue avec le nouveau timeout
2. 📊 Vérifier les logs GitHub Actions du dernier build
3. 🔍 Vérifier que `server.js` existe dans l'image Docker déployée
4. 🧪 Tester le build localement si nécessaire

---

## 🎯 Résultat Attendu

Après correction:
- ✅ Serveur répond aux requêtes HTTP
- ✅ Health check: HEALTHY
- ✅ ALB: 200 OK
- ✅ Site accessible

---

**Status:** 🔍 En investigation

