# Installation Node.js 20 pour Strapi

## Problème

Vous avez Node.js 25.2.1, mais Strapi 4.18.0 nécessite Node.js 18-20.

## Solution : Installer nvm et Node.js 20

### 1. Installer nvm

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
```

Puis redémarrer votre terminal ou exécuter :
```bash
source ~/.zshrc  # ou ~/.bashrc selon votre shell
```

### 2. Installer Node.js 20

```bash
nvm install 20
nvm use 20
```

### 3. Vérifier

```bash
node --version  # Devrait afficher v20.x.x
```

### 4. Démarrer Strapi

```bash
cd services/arquantix/cms
npm install
npm run develop
```

## Alternative : Utiliser Docker

Si vous préférez ne pas installer nvm, utilisez Docker :

```bash
# Depuis la racine du repo
docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-cms
```

---

**Dernière mise à jour:** 2026-01-01


