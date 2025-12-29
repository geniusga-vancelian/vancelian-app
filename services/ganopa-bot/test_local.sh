#!/bin/bash
# Test local du bot Ganopa avant déploiement

set -euo pipefail

echo "🧪 Test local du bot Ganopa"
echo "============================"
echo ""

# Vérifier que les variables d'environnement sont définies
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "⚠️  TELEGRAM_BOT_TOKEN non défini. Utilisez: export TELEGRAM_BOT_TOKEN=..."
    exit 1
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "⚠️  OPENAI_API_KEY non défini. Utilisez: export OPENAI_API_KEY=..."
    exit 1
fi

WEBHOOK_SECRET="${WEBHOOK_SECRET:-Azerty0334}"

echo "✅ Variables d'environnement OK"
echo ""

# Test 1: Compilation Python
echo "📝 Test 1: Compilation Python"
python3 -m compileall services/ganopa-bot/app -q
if [ $? -eq 0 ]; then
    echo "✅ Compilation OK"
else
    echo "❌ Erreur de compilation"
    exit 1
fi
echo ""

# Test 2: Vérifier que le serveur démarre
echo "📝 Test 2: Vérification des imports"
cd services/ganopa-bot
python3 -c "from app.main import app; print('✅ Imports OK')" || {
    echo "❌ Erreur d'import"
    exit 1
}
cd ../..
echo ""

# Test 3: Test de l'endpoint /health
echo "📝 Test 3: Endpoint /health"
echo "Démarrez le serveur avec: cd services/ganopa-bot && uvicorn app.main:app --reload --port 8000"
echo "Puis dans un autre terminal:"
echo "  curl http://localhost:8000/health"
echo ""

# Test 4: Test de l'endpoint /_meta
echo "📝 Test 4: Endpoint /_meta"
echo "  curl http://localhost:8000/_meta | jq"
echo ""

# Test 5: Test du webhook Telegram (POST)
echo "📝 Test 5: Webhook Telegram (POST)"
echo "Exécutez cette commande (remplacez <CHAT_ID> par votre chat_id Telegram):"
echo ""
cat << 'EOF'
curl -X POST http://localhost:8000/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: Azerty0334" \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 1,
      "from": {"id": 123456, "is_bot": false, "first_name": "Test"},
      "chat": {"id": <CHAT_ID>, "type": "private"},
      "date": 1234567890,
      "text": "Hello"
    }
  }'
EOF
echo ""
echo "Vérifiez que la réponse immédiate est: {\"ok\": true}"
echo "Vérifiez les logs pour voir:"
echo "  - telegram_webhook_post"
echo "  - telegram_message_extracted"
echo "  - openai_request_start"
echo "  - openai_request_success"
echo "  - telegram_send_start"
echo "  - telegram_send_success"
echo ""

echo "✅ Tests locaux préparés"
echo ""
echo "Pour démarrer le serveur:"
echo "  cd services/ganopa-bot"
echo "  export TELEGRAM_BOT_TOKEN=..."
echo "  export OPENAI_API_KEY=..."
echo "  export WEBHOOK_SECRET=Azerty0334"
echo "  uvicorn app.main:app --reload --port 8000"

