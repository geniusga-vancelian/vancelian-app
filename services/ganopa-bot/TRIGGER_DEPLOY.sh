#!/bin/bash
set -euo pipefail

# Script pour déclencher le workflow GitHub Actions manuellement

echo "🚀 Déclenchement du workflow GitHub Actions..."
echo ""

# Vérifier si gh CLI est disponible
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI détecté"
    echo ""
    echo "Déclenchement du workflow 'Deploy Ganopa Bot (ECS Fargate)'..."
    gh workflow run "Deploy Ganopa Bot (ECS Fargate).yml" \
        -f target_env=dev
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Workflow déclenché avec succès!"
        echo ""
        echo "📊 Pour suivre le déploiement:"
        echo "   https://github.com/geniusga-vancelian/vancelian-app/actions"
        echo ""
    else
        echo ""
        echo "❌ Erreur lors du déclenchement du workflow"
        echo "   Vérifiez que vous êtes authentifié: gh auth login"
        exit 1
    fi
else
    echo "⚠️  GitHub CLI (gh) n'est pas installé"
    echo ""
    echo "📋 Instructions manuelles:"
    echo "   1. Aller sur: https://github.com/geniusga-vancelian/vancelian-app/actions"
    echo "   2. Sélectionner 'Deploy Ganopa Bot (ECS Fargate)'"
    echo "   3. Cliquer sur 'Run workflow'"
    echo "   4. Sélectionner 'dev' comme environnement"
    echo "   5. Cliquer sur 'Run workflow'"
    echo ""
    echo "💡 Ou installer GitHub CLI:"
    echo "   brew install gh"
    echo "   gh auth login"
    exit 1
fi


