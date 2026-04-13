#!/bin/bash
# Démarre uniquement l'émulateur Android (sans lancer l'app)

export PATH="/opt/homebrew/bin:$PATH"
export ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"

if adb devices 2>/dev/null | grep -q emulator; then
  echo "→ Un émulateur est déjà démarré."
  adb devices
  exit 0
fi

echo "→ Démarrage de l'émulateur arquantix_phone..."
exec emulator -avd arquantix_phone -no-snapshot-load
