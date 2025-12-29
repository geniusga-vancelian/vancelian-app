#!/bin/bash
# Lint Python - compilation et vérification de syntaxe

set -euo pipefail

echo "🔍 Lint Python - Ganopa Bot"
echo "============================"
echo ""

# Changer dans le répertoire du service
cd "$(dirname "$0")" || exit 1

# Compilation Python
echo "📝 Compilation Python..."
python3 -m compileall app -q

if [ $? -eq 0 ]; then
    echo "✅ Compilation OK"
else
    echo "❌ Erreur de compilation"
    exit 1
fi
echo ""

# Vérification des imports
echo "📝 Vérification des imports..."
python3 -c "from app.main import app; from app.config import SERVICE_NAME; print(f'✅ Imports OK - Service: {SERVICE_NAME}')" || {
    echo "❌ Erreur d'import"
    exit 1
}
echo ""

# Vérification de la syntaxe avec flake8 (si disponible)
if command -v flake8 &> /dev/null; then
    echo "📝 Vérification flake8..."
    flake8 app/ --max-line-length=120 --ignore=E501,W503 || {
        echo "⚠️  flake8 a trouvé des problèmes (non bloquant)"
    }
    echo ""
fi

echo "✅ Lint terminé"

