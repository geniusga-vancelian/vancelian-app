#!/bin/bash
# Lance l'app Flutter sur l'émulateur Android
# Prérequis : émulateur démarré (ou lance automatiquement)

set -e

export PATH="/opt/homebrew/bin:$PATH"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
export ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck source=scripts/flutter_local_env.sh
source "$SCRIPT_DIR/scripts/flutter_local_env.sh"

API_URL="${API_BASE_URL:-http://10.0.2.2:3000}"
if [ -n "${AUTH_API_BASE_URL:-}" ]; then
  AUTH_URL="$AUTH_API_BASE_URL"
else
  AUTH_URL="${API_URL/:3000/:8000}"
fi
echo "→ API URL: $API_URL (10.0.2.2 = localhost de la machine)"
echo "→ Auth API URL: $AUTH_URL"
echo ""

# Vérifier si l'émulateur est déjà démarré
if ! adb devices | grep -q emulator; then
  echo "→ Démarrage de l'émulateur Android (arquantix_phone)..."
  emulator -avd arquantix_phone -no-snapshot-load &
  EMU_PID=$!
  echo "  Attente du boot (~90s)..."
  sleep 30
  adb wait-for-device
  sleep 60
fi

echo "→ flutter pub get"
flutter pub get

echo ""
echo "→ Lancement de l'app sur Android..."
# Flutter n'associe pas toujours "android" à l'émulateur ; utiliser l'ID explicite
ANDROID_DEVICE=$(flutter devices 2>/dev/null | grep "emulator-" | awk -F' • ' '{print $2}' | awk '{print $1}')
if [ -n "$ANDROID_DEVICE" ]; then
  flutter run -d "$ANDROID_DEVICE" \
    --dart-define=API_BASE_URL="$API_URL" \
    --dart-define=AUTH_API_BASE_URL="$AUTH_URL" \
    "${FLUTTER_EXTRA_DART_DEFINES[@]}" "$@"
else
  flutter run -d android \
    --dart-define=API_BASE_URL="$API_URL" \
    --dart-define=AUTH_API_BASE_URL="$AUTH_URL" \
    "${FLUTTER_EXTRA_DART_DEFINES[@]}" "$@"
fi
