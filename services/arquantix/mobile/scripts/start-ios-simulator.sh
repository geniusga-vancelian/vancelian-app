#!/bin/bash
# Ouvre le simulateur iOS (iPhone) sans lancer l'app Flutter
# Prérequis : Xcode installé et configuré (xcode-select)

set -e

if [ ! -d /Applications/Xcode.app ]; then
  echo "❌ Xcode n'est pas installé. Installez-le depuis l'App Store."
  exit 1
fi

# Ouvrir l'app Simulateur (incluse avec Xcode)
open -a Simulator

echo "→ Simulateur iOS lancé."
echo "  Pour lancer l'app Arquantix News dessus : arq-ios"
