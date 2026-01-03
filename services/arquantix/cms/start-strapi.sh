#!/bin/bash
# Script pour démarrer Strapi avec nvm

cd "$(dirname "$0")"

# Charger nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Utiliser Node.js 20
nvm use 20

# Démarrer Strapi
npm run develop


