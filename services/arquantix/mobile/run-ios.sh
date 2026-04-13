#!/bin/bash
# Lance l'app Flutter sur le **simulateur** iOS uniquement.
# Pour un **iPhone réel** : ./run-ios-device.sh (sinon 127.0.0.1 = le téléphone → API injoignable).
# Prérequis : Xcode installé (App Store) + avoir exécuté une fois :
#   sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
#   sudo xcodebuild -runFirstLaunch
#   (optionnel) brew install cocoapods

set -e

export PATH="/opt/homebrew/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck source=/dev/null
source "$SCRIPT_DIR/scripts/ios_dev_network.sh"
if [ -n "${API_BASE_URL:-}" ]; then
  echo "→ API URL: $API_URL (API_BASE_URL fourni)"
elif [[ "$API_URL" != *"127.0.0.1"* ]]; then
  echo "→ API URL: $API_URL (IP du Mac)"
else
  echo "→ API URL: $API_URL (127.0.0.1)"
fi
echo "→ Auth API URL: $AUTH_URL"
echo ""

# Vérifier que Xcode est disponible
if ! command -v xcodebuild &>/dev/null; then
  echo "❌ Xcode n'est pas installé ou pas sélectionné."
  echo ""
  echo "Pour installer le simulateur iOS :"
  echo "  1. Installez Xcode depuis l’App Store (https://apps.apple.com/app/xcode/id497799835)"
  echo "  2. Ouvrez Xcode une fois et acceptez la licence"
  echo "  3. Dans un terminal :"
  echo "     sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"
  echo "     sudo xcodebuild -runFirstLaunch"
  echo "  4. (Recommandé) Installez CocoaPods : brew install cocoapods"
  echo ""
  exit 1
fi

# Vérifier qu'un runtime iOS est installé (sinon aucun simulateur n'apparaît)
if ! xcrun simctl list devices available 2>/dev/null | grep -q "iPhone"; then
  echo "❌ Aucun simulateur iPhone disponible."
  echo ""
  echo "Il manque le runtime iOS. Dans Xcode :"
  echo "  1. Ouvrez Xcode"
  echo "  2. Menu Xcode > Settings… (ou Preferences)"
  echo "  3. Onglet « Platforms » (ou « Components »)"
  echo "  4. Cliquez sur « + » et téléchargez une version iOS (ex. iOS 18.x)"
  echo "  5. Attendez la fin du téléchargement, puis relancez : arq-ios"
  echo ""
  exit 1
fi

# Build dans /tmp pour éviter codesign "resource fork not allowed" (OneDrive)
BUILD_LINK="/tmp/arquantix_mobile_build"
rm -rf "$SCRIPT_DIR/build"
if [ ! -d "$BUILD_LINK" ]; then
  mkdir -p "$BUILD_LINK"
fi
ln -s "$BUILD_LINK" "$SCRIPT_DIR/build"
echo "→ Build iOS dans /tmp (évite erreur codesign OneDrive)"

echo "→ flutter pub get"
flutter pub get

# Démarrer un simulateur si aucun n'est déjà démarré (Flutter ne voit que les simulateurs bootés)
BOOTED=$(xcrun simctl list devices available | grep -E "iPhone.*Booted" | head -1)
if [ -z "$BOOTED" ]; then
  echo ""
  echo "→ Démarrage d'un simulateur iPhone..."
  UDID=$(xcrun simctl list devices available | grep "iPhone" | head -1 | grep -oE '[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}')
  if [ -n "$UDID" ]; then
    xcrun simctl boot "$UDID" 2>/dev/null || true
    open -a Simulator
    sleep 4
  fi
fi

echo ""
echo "→ Lancement sur le simulateur iOS..."
# Flutter n'accepte pas toujours "-d ios" : on cible le premier iPhone par son UDID
UDID=$(xcrun simctl list devices available | grep "iPhone" | head -1 | grep -oE '[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}')
if [ -z "$UDID" ]; then
  echo "❌ Aucun UDID iPhone trouvé."
  exit 1
fi
echo "   (cible: $UDID)"
# Désinstaller l'app du simulateur pour éviter "No such process" (install propre)
xcrun simctl uninstall "$UDID" com.example.arquantixNews 2>/dev/null || true
flutter run -d "$UDID" --dart-define=API_BASE_URL="$API_URL" --dart-define=AUTH_API_BASE_URL="$AUTH_URL" "$@"
