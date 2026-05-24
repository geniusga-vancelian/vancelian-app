#!/bin/bash
# Lance Flutter sur un iPhone / iPad PHYSIQUE (USB ou réseau).
#
# Modèle officiel :
#   BFF Next     → http://<IP_LAN_DU_MAC>:3000   (API_BASE_URL)
#   FastAPI auth → http://<IP_LAN_DU_MAC>:8000   (AUTH_API_BASE_URL)
#   Jamais localhost / 127.0.0.1 : sur l’iPhone ils désignent le téléphone, pas le Mac.
#
# Prérequis : Next sur le port 3000 et API sur 8000 joignables depuis le LAN
# (Docker compose publie en général ces ports sur 0.0.0.0). Mac et iPhone sur le même Wi‑Fi
# (sauf tunnel USB avancé).
#
# Usage :
#   ./run-ios-device.sh
#   FLUTTER_DEVICE_ID=<udid> ./run-ios-device.sh   # forcer un appareil
#   API_BASE_URL=http://192.168.1.10:3000 AUTH_API_BASE_URL=http://192.168.1.10:8000 ./run-ios-device.sh
#
set -e

export PATH="/opt/homebrew/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck source=scripts/flutter_local_env.sh
source "$SCRIPT_DIR/scripts/flutter_local_env.sh"

# Détection IP LAN pour les défauts (en0 / en1) — voir scripts/ios_dev_network.sh
export ARQUANTIX_IOS_USE_LAN_DEFAULT=1

# shellcheck source=/dev/null
source "$SCRIPT_DIR/scripts/ios_dev_network.sh"

echo ""
echo "━━ iPhone physique — cibles attendues ━━"
echo "  BFF Next.js   : http://<IP_LAN_MAC>:3000"
echo "  FastAPI auth  : http://<IP_LAN_MAC>:8000"
echo "  Doc : docs/LOCAL_IOS_AND_BFF.md"
echo ""

echo "→ API URL (BFF) :     $API_URL"
echo "→ Auth API URL :      $AUTH_URL"
echo ""

if [[ "$API_URL" == *"127.0.0.1"* ]] || [[ "$API_URL" == *"localhost"* ]]; then
  echo "❌ Refus : localhost / 127.0.0.1 ne permettent pas d’atteindre le Mac depuis un iPhone réel."
  echo "   Le script n’a pas trouvé d’IP LAN (en0/en1). Vérifiez le Wi‑Fi ou définissez :"
  echo "     export API_BASE_URL=http://<IP_DU_MAC>:3000"
  echo "     export AUTH_API_BASE_URL=http://<IP_DU_MAC>:8000"
  echo ""
  echo "   Exemples corrects :"
  echo "     API_BASE_URL=http://192.168.1.42:3000 AUTH_API_BASE_URL=http://192.168.1.42:8000 ./run-ios-device.sh"
  echo ""
  echo "   IP(s) souvent utiles sur ce Mac :"
  for _iface in en0 en1; do
    _ip=$(ipconfig getifaddr "$_iface" 2>/dev/null || true)
    if [ -n "$_ip" ]; then
      echo "     $_iface → $_ip"
    fi
  done
  echo ""
  echo "   Pour ignorer ce blocage (rare) : ARQUANTIX_ALLOW_LOCALHOST_ON_DEVICE=1"
  echo ""
  if [[ "${ARQUANTIX_ALLOW_LOCALHOST_ON_DEVICE:-}" != "1" ]]; then
    exit 1
  fi
  echo "⚠️  Poursuite avec URL locale — comportement probablement cassé sur appareil physique."
  echo ""
fi
echo ""

BUILD_LINK="/tmp/arquantix_mobile_build"
rm -rf "$SCRIPT_DIR/build"
if [ ! -d "$BUILD_LINK" ]; then
  mkdir -p "$BUILD_LINK"
fi
ln -sf "$BUILD_LINK" "$SCRIPT_DIR/build"
echo "→ Build iOS dans /tmp (évite codesign OneDrive)"

echo "→ flutter pub get"
flutter pub get

DEVICE_ID="${FLUTTER_DEVICE_ID:-}"
if [ -z "$DEVICE_ID" ]; then
  DEVICE_ID=$(flutter devices --machine 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(1)
for d in data:
    if d.get('targetPlatform') == 'ios' and d.get('emulator') is False:
        print(d.get('id', '') or '', end='')
        sys.exit(0)
sys.exit(1)
") || true
fi

if [ -z "$DEVICE_ID" ]; then
  echo "❌ Aucun appareil iOS physique détecté."
  echo "   Branchez l’iPhone (câble ou réseau), déverrouillez-le, acceptez « Faire confiance »."
  echo "   Liste : flutter devices"
  exit 1
fi

echo "→ Cible : $DEVICE_ID"
echo ""
flutter run -d "$DEVICE_ID" \
  --dart-define=API_BASE_URL="$API_URL" \
  --dart-define=AUTH_API_BASE_URL="$AUTH_URL" \
  "${FLUTTER_EXTRA_DART_DEFINES[@]}" "$@"
