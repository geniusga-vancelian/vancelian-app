#!/usr/bin/env bash
# Lancer toute la stack Arquantix (Docker/DB + API + Web).
# Dans Terminal :  bash scripts/lancer-arquantix.command
# Ou :  cd /chemin/arquantix && make boot
cd "$(dirname "$0")/.."
make boot
echo ""
read -p "Appuyez sur Entrée pour fermer cette fenêtre."
