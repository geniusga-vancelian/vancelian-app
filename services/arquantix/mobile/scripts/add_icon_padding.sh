#!/usr/bin/env bash
# Génère une icône 1024x1024 avec padding autour du logo (style Fichiers / Fitness).
# Nécessite ImageMagick (brew install imagemagick).
# Usage: depuis mobile/ : ./scripts/add_icon_padding.sh

set -e
SRC="assets/app_icon_1024.png"
OUT="assets/app_icon_1024_padded.png"
# Logo à ~82 % pour laisser ~9 % de marge de chaque côté
SIZE=820
# Fond : gris foncé (ajuster si ton différent, ex. #1C1C1E)
BG="#2C2C2E"

if ! command -v convert &>/dev/null; then
  echo "ImageMagick requis: brew install imagemagick"
  exit 1
fi
if [[ ! -f "$SRC" ]]; then
  echo "Fichier source introuvable: $SRC"
  exit 1
fi

convert "$SRC" -resize "${SIZE}x${SIZE}" -gravity center -background "$BG" -extent 1024x1024 "$OUT"
echo "Créé: $OUT"

read -p "Remplacer l’icône source par la version avec padding ? (o/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[oOyY]$ ]]; then
  cp "$SRC" "${SRC}.bak"
  cp "$OUT" "$SRC"
  echo "Fait. Original sauvegardé dans ${SRC}.bak"
  echo "Puis: dart run flutter_launcher_icons"
fi
