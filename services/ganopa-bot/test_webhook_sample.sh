#!/bin/bash
# Script de test pour le webhook Telegram (exemple avec chat_id)

set -euo pipefail

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-Azerty0334}"
CHAT_ID="${CHAT_ID:-123456789}"  # Remplacez par votre chat_id Telegram

echo "🧪 Test du webhook Telegram"
echo "============================"
echo ""
echo "URL: ${BASE_URL}/telegram/webhook"
echo "Chat ID: ${CHAT_ID}"
echo ""

# Test POST avec payload Telegram sample
echo "📤 Envoi d'un message 'Hello'..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X POST "${BASE_URL}/telegram/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: ${WEBHOOK_SECRET}" \
  -d "{
    \"update_id\": $(date +%s),
    \"message\": {
      \"message_id\": 1,
      \"from\": {
        \"id\": ${CHAT_ID},
        \"is_bot\": false,
        \"first_name\": \"Test\"
      },
      \"chat\": {
        \"id\": ${CHAT_ID},
        \"type\": \"private\"
      },
      \"date\": $(date +%s),
      \"text\": \"Hello\"
    }
  }")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

echo "Réponse HTTP: ${HTTP_CODE}"
echo "Body: ${BODY}"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | grep -q '"ok":true'; then
        echo "✅ Réponse immédiate OK: {\"ok\": true}"
        echo ""
        echo "⚠️  Vérifiez les logs du serveur pour confirmer:"
        echo "  - telegram_webhook_post"
        echo "  - telegram_message_extracted"
        echo "  - openai_request_start"
        echo "  - openai_request_success"
        echo "  - telegram_send_start"
        echo "  - telegram_send_success"
    else
        echo "❌ Réponse inattendue: ${BODY}"
        exit 1
    fi
else
    echo "❌ Erreur HTTP: ${HTTP_CODE}"
    echo "Body: ${BODY}"
    exit 1
fi

