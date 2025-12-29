#!/bin/bash
set -euo pipefail

echo "🧪 Testing Doc-Memory Agent Mode"
echo "=================================="

# Default values
CHAT_ID="${CHAT_ID:-123456789}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-Azerty0334}"
DOCS_DIR="${DOCS_DIR:-../../docs}"

echo "Using CHAT_ID: $CHAT_ID"
echo "Using WEBHOOK_SECRET: $WEBHOOK_SECRET"
echo "Using DOCS_DIR: $DOCS_DIR"
echo ""

# Check if docs directory exists
if [ ! -d "$DOCS_DIR" ]; then
    echo "⚠️  Docs directory not found: $DOCS_DIR"
    echo "   Will use fallback (no-docs)"
    echo ""
fi

# Start uvicorn in background
echo "🚀 Starting uvicorn..."
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-dummy_token_for_testing}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy_key_for_testing}"
export WEBHOOK_SECRET="$WEBHOOK_SECRET"
export DOCS_DIR="$DOCS_DIR"
export DOCS_REFRESH_SECONDS=300
export MEMORY_TTL_SECONDS=1800
export MEMORY_MAX_MESSAGES=20

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!
echo "Uvicorn PID: $UVICORN_PID"
echo ""

# Give uvicorn a moment to start
sleep 3

echo "--- Test 1: GET /_meta (check docs_hash) ---"
curl -s http://localhost:8000/_meta | jq .
echo ""

echo "--- Test 2: First message (should have 'J'ai bien relu...' prefix) ---"
curl -s -X POST http://localhost:8000/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $WEBHOOK_SECRET" \
  -d "{
    \"update_id\": 100001,
    \"message\": {
      \"message_id\": 1,
      \"from\": {\"id\": $CHAT_ID, \"is_bot\": false, \"first_name\": \"Test\", \"username\": \"testuser\"},
      \"chat\": {\"id\": $CHAT_ID, \"first_name\": \"Test\", \"username\": \"testuser\", \"type\": \"private\"},
      \"date\": $(date +%s),
      \"text\": \"Hello, what is the architecture of this system?\"
    }
  }" | jq .
echo ""

echo "⏳ Waiting 2 seconds for background processing..."
sleep 2
echo ""

echo "--- Test 3: Second message (should NOT have prefix, uses memory) ---"
curl -s -X POST http://localhost:8000/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $WEBHOOK_SECRET" \
  -d "{
    \"update_id\": 100002,
    \"message\": {
      \"message_id\": 2,
      \"from\": {\"id\": $CHAT_ID, \"is_bot\": false, \"first_name\": \"Test\", \"username\": \"testuser\"},
      \"chat\": {\"id\": $CHAT_ID, \"first_name\": \"Test\", \"username\": \"testuser\", \"type\": \"private\"},
      \"date\": $(date +%s),
      \"text\": \"What about the deployment process?\"
    }
  }" | jq .
echo ""

echo "⏳ Waiting 2 seconds for background processing..."
sleep 2
echo ""

echo "--- Test 4: GET /_meta again (check memory stats) ---"
curl -s http://localhost:8000/_meta | jq .
echo ""

# Clean up
echo "Shutting down uvicorn..."
kill "$UVICORN_PID"
wait "$UVICORN_PID" || true
echo ""

echo "✅ Test finished!"
echo ""
echo "Expected results:"
echo "  - Test 2: Response should start with 'J'ai bien relu toute la doc (version: ...)'"
echo "  - Test 3: Response should NOT have prefix (memory exists)"
echo "  - Test 4: memory_active_chats should be >= 1"

