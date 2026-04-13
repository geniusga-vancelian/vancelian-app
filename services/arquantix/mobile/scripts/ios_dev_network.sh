# shellcheck shell=bash
# URLs BFF Next (3000) + FastAPI auth (8000) pour Flutter --dart-define.
# À sourcer depuis run-ios.sh / run-ios-device.sh :
#   source "$SCRIPT_DIR/scripts/ios_dev_network.sh"
#
# Sur iPhone réel : définir API_BASE_URL / AUTH_API_BASE_URL si besoin, ou laisser
# la détection de l’IP LAN (en0/en1).

if [ -n "${API_BASE_URL:-}" ]; then
  API_URL="$API_BASE_URL"
else
  MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)
  if [ -n "$MAC_IP" ]; then
    API_URL="http://${MAC_IP}:3000"
  else
    API_URL="http://127.0.0.1:3000"
  fi
fi

if [ -n "${AUTH_API_BASE_URL:-}" ]; then
  AUTH_URL="$AUTH_API_BASE_URL"
else
  AUTH_URL="${API_URL/:3000/:8000}"
  AUTH_URL="${AUTH_URL/:3001/:8000}"
fi

export API_URL AUTH_URL
