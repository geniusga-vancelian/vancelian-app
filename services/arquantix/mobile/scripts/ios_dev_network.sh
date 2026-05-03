# shellcheck shell=bash
# Ports officiels locaux : BFF Next.js **3000**, FastAPI (auth / sécurisé) **8000**.
#
# Sourcer depuis run-ios.sh ou run-ios-device.sh uniquement.
#
# Modèle :
#   - Simulateur : ne pas exporter ARQUANTIX_IOS_USE_LAN_DEFAULT (ou =0) → défaut
#     http://127.0.0.1:3000 et auth http://127.0.0.1:8000 si API_BASE_URL absent.
#   - iPhone physique : export ARQUANTIX_IOS_USE_LAN_DEFAULT=1 avant source →
#     si API_BASE_URL absent, dérive http://<IP_LAN>:3000 depuis en0/en1.

if [ "${ARQUANTIX_IOS_USE_LAN_DEFAULT:-0}" = "1" ]; then
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
else
  if [ -n "${API_BASE_URL:-}" ]; then
    API_URL="$API_BASE_URL"
  else
    API_URL="http://127.0.0.1:3000"
  fi
fi

if [ -n "${AUTH_API_BASE_URL:-}" ]; then
  AUTH_URL="$AUTH_API_BASE_URL"
else
  AUTH_URL="${API_URL/:3000/:8000}"
fi

export API_URL AUTH_URL
