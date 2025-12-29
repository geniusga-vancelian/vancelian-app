#!/bin/bash
# Test local du bot Ganopa - démarre uvicorn et teste les endpoints

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
PORT="${PORT:-8000}"

echo "✅ Variables d'environnement OK"
echo "  PORT: ${PORT}"
echo ""

# Changer dans le répertoire du service
cd "$(dirname "$0")" || exit 1

# Démarrer uvicorn en arrière-plan
echo "🚀 Démarrage de uvicorn sur le port ${PORT}..."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" > /tmp/ganopa-bot-test.log 2>&1 &
UVICORN_PID=$!

# Attendre que le serveur démarre
echo "⏳ Attente du démarrage du serveur..."
sleep 3

# Vérifier que le processus est toujours actif
if ! kill -0 "${UVICORN_PID}" 2>/dev/null; then
    echo "❌ uvicorn n'a pas démarré correctement"
    cat /tmp/ganopa-bot-test.log
    exit 1
fi

echo "✅ Serveur démarré (PID: ${UVICORN_PID})"
echo ""

# Test 1: /health
echo "📝 Test 1: GET /health"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://localhost:${PORT}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$HEALTH_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ /health: HTTP ${HTTP_CODE}"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo "❌ /health: HTTP ${HTTP_CODE}"
    echo "$BODY"
fi
echo ""

# Test 2: /_meta
echo "📝 Test 2: GET /_meta"
META_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://localhost:${PORT}/_meta")
HTTP_CODE=$(echo "$META_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$META_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ /_meta: HTTP ${HTTP_CODE}"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
    
    # Vérifier la présence de la version
    if echo "$BODY" | jq -e '.version' >/dev/null 2>&1; then
        VERSION=$(echo "$BODY" | jq -r '.version')
        echo "✅ Version détectée: ${VERSION}"
    fi
else
    echo "❌ /_meta: HTTP ${HTTP_CODE}"
    echo "$BODY"
fi
echo ""

# Test 3: Vérifier les headers
echo "📝 Test 3: Headers HTTP"
HEADERS=$(curl -s -I "http://localhost:${PORT}/_meta")
if echo "$HEADERS" | grep -qi "x-ganopa-version"; then
    echo "✅ Header X-Ganopa-Version présent"
    echo "$HEADERS" | grep -i "x-ganopa"
else
    echo "❌ Header X-Ganopa-Version manquant"
fi
echo ""

# Arrêter uvicorn
echo "🛑 Arrêt du serveur..."
kill "${UVICORN_PID}" 2>/dev/null || true
wait "${UVICORN_PID}" 2>/dev/null || true

echo ""
echo "✅ Tests locaux terminés"
echo ""
echo "📋 Logs du serveur:"
echo "   cat /tmp/ganopa-bot-test.log"
