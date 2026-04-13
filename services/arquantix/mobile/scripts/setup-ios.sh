#!/bin/bash
# Vérifie et guide la configuration pour le simulateur iOS (Xcode + CocoaPods)
# À lancer une fois avant d'utiliser arq-ios

set -e

echo "=== Configuration iOS pour Arquantix News ==="
echo ""

# 1. Xcode installé ?
if [ ! -d /Applications/Xcode.app ]; then
  echo "❌ Xcode n'est pas installé."
  echo "   → Installez-le depuis l'App Store : https://apps.apple.com/app/xcode/id497799835"
  echo "   → Puis relancez ce script."
  exit 1
fi
echo "✓ Xcode.app trouvé"

# 2. xcode-select pointe-t-il sur Xcode ?
CURRENT=$(xcode-select -p 2>/dev/null || true)
if [ "$CURRENT" != "/Applications/Xcode.app/Contents/Developer" ]; then
  echo ""
  echo "⚠️  La ligne de commande n'utilise pas encore Xcode."
  echo "   Exécutez dans votre terminal (mot de passe demandé) :"
  echo ""
  echo "   sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"
  echo "   sudo xcodebuild -runFirstLaunch"
  echo ""
  read -p "Appuyez sur Entrée après avoir exécuté ces commandes (ou Ctrl+C pour quitter)..." _
fi
echo "✓ xcode-select : $(xcode-select -p 2>/dev/null)"

# 3. xcodebuild fonctionne ?
if ! xcodebuild -version &>/dev/null; then
  echo "❌ xcodebuild échoue. Vérifiez que vous avez bien exécuté :"
  echo "   sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"
  echo "   sudo xcodebuild -runFirstLaunch"
  exit 1
fi
echo "✓ xcodebuild OK"
xcodebuild -version | head -1

# 4. CocoaPods
if ! command -v pod &>/dev/null; then
  echo ""
  echo "Installation de CocoaPods..."
  brew install cocoapods
fi
echo "✓ CocoaPods : $(pod --version 2>/dev/null)"

echo ""
echo "=== Configuration iOS prête ==="
echo "Vous pouvez lancer l'app sur le simulateur avec :"
echo "  arq-ios"
echo "ou :"
echo "  cd services/arquantix/mobile && API_BASE_URL=http://localhost:3001 ./run-ios.sh"
echo ""
