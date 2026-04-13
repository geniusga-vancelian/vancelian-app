#!/bin/bash
# Lance Flutter sur un iPhone / iPad PHYSIQUE (USB ou réseau).
# Passe API_BASE_URL + AUTH_API_BASE_URL vers l’IP LAN du Mac — obligatoire car
# localhost / 127.0.0.1 sur l’appareil pointe vers le téléphone, pas votre Mac.
#
# Prérequis : API FastAPI sur le Mac avec --host 0.0.0.0 --port 8000, Next sur :3000,
# même Wi‑Fi (ou USB avec tunnel si vous savez ce que vous faites).
#
# Usage :
#   ./run-ios-device.sh
#   FLUTTER_DEVICE_ID=<udid> ./run-ios-device.sh   # forcer un appareil
#
set -e

export PATH="/opt/homebrew/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/scripts/ios_dev_network.sh"

echo "→ API URL (BFF):     $API_URL"
echo "→ Auth API URL:      $AUTH_URL"
if [[ "$API_URL" == *"127.0.0.1"* ]] || [[ "$API_URL" == *"localhost"* ]]; then
  echo ""
  echo "⚠️  URL en localhost : un iPhone réel ne pourra pas joindre le Mac."
  echo "   Branchez le Wi‑Fi ou exportez API_BASE_URL=http://<IP_LAN>:3000"
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
  "$@"
