#!/bin/bash
# Script pour lancer l'app Flutter Arquantix News
# Prérequis : Flutter installé (brew install --cask flutter)

set -e

# S'assurer que Flutter, Java et Android SDK sont dans le PATH
export PATH="/opt/homebrew/bin:$PATH"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
export ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck source=scripts/flutter_local_env.sh
source "$SCRIPT_DIR/scripts/flutter_local_env.sh"

# URL API (Next.js sur port 3000)
# - iOS Simulator : localhost fonctionne
# - Android émulateur : utiliser API_BASE_URL=http://10.0.2.2:3000 ./run.sh
API_URL="${API_BASE_URL:-http://localhost:3000}"
if [ -n "${AUTH_API_BASE_URL:-}" ]; then
  AUTH_URL="$AUTH_API_BASE_URL"
else
  AUTH_URL="${API_URL/:3000/:8000}"
fi

echo "→ API URL: $API_URL"
echo "→ Auth API URL: $AUTH_URL"
echo ""

# Générer le projet si nécessaire (android/, ios/ manquants)
if [ ! -d "android" ] || [ ! -d "ios" ]; then
  echo "→ Génération du projet Flutter..."
  flutter create . --project-name arquantix_news
fi

echo "→ flutter pub get"
flutter pub get

echo ""
echo "→ Lancement de l'app..."
flutter run --dart-define=API_BASE_URL="$API_URL" --dart-define=AUTH_API_BASE_URL="$AUTH_URL" \
  "${FLUTTER_EXTRA_DART_DEFINES[@]}" "$@"
