#!/bin/bash
# Ouvre le simulateur iOS (iPhone) sans lancer l'app Flutter
# Prérequis : Xcode installé et configuré (xcode-select)

set -e

MOBILE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -d /Applications/Xcode.app ]; then
  echo "❌ Xcode n'est pas installé. Installez-le depuis l'App Store."
  exit 1
fi

# Ouvrir l'app Simulateur (incluse avec Xcode)
open -a Simulator

echo "→ Simulateur iOS lancé."
echo "  Pour lancer l’app : arq-ios  ou  ./run-ios.sh"
echo "  Réseau dev (simulateur = 127.0.0.1:3000 / :8000 ; iPhone = IP LAN) :"
echo "    $MOBILE_ROOT/docs/LOCAL_IOS_AND_BFF.md"
