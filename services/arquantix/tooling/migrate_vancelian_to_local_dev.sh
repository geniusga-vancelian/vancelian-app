#!/usr/bin/env bash
# Migration sûre : copie OneDrive → ~/dev/vancelian-app (pas de mv, pas de perte Git).
# Usage :
#   ./migrate_vancelian_to_local_dev.sh copy    # rsync miroir
#   ./migrate_vancelian_to_local_dev.sh verify  # dry-run (doit être vide si OK)
#   ./migrate_vancelian_to_local_dev.sh xattr    # nettoie xattrs (hors .git/objects)
#   ./migrate_vancelian_to_local_dev.sh all     # copy puis verify puis xattr
#
# Surcharges : SOURCE=... DEST=... ./migrate_vancelian_to_local_dev.sh copy
set -euo pipefail

SOURCE_DEFAULT="${HOME}/Library/CloudStorage/OneDrive-Vancelian/Documents/vancelian-app"
DEST_DEFAULT="${HOME}/dev/vancelian-app"
SOURCE="${SOURCE:-$SOURCE_DEFAULT}"
DEST="${DEST:-$DEST_DEFAULT}"

blue() { printf "\033[1;34m%s\033[0m\n" "$*"; }
green() { printf "\033[1;32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[1;33m%s\033[0m\n" "$*"; }
red() { printf "\033[1;31m%s\033[0m\n" "$*"; }

usage() {
  cat <<EOF
Usage: $(basename "$0") copy | verify | xattr | all

  copy   — rsync -avh --progress (miroir vers DEST, sans supprimer la source)
  verify — rsync --dry-run (itemize ; quelques écarts metadata possibles)
  xattr  — retire les xattrs macOS hors arborescence .git/* (évite Errno 13 sur objects)
  all    — copy, verify, du (réassurance), xattr, git status

SOURCE=${SOURCE}
DEST=${DEST}
EOF
}

need_src() {
  if [ ! -d "$SOURCE" ]; then
    red "SOURCE introuvable : $SOURCE"
    exit 1
  fi
  if [ ! -d "$SOURCE/.git" ] && [ ! -f "$SOURCE/.git" ]; then
    yellow "Attention : pas de .git visible dans SOURCE (dépôt nu ou sous-module ?). Vérifie avant de t’appuyer sur cette copie."
  fi
}

# DEST doit être absent ou un dossier (jamais un fichier / lien vers fichier).
guard_dest_is_dir_or_absent() {
  if [ -e "$DEST" ] && [ ! -d "$DEST" ]; then
    red "DEST existe mais n’est pas un dossier : $DEST"
    exit 1
  fi
}

cmd_copy() {
  need_src
  guard_dest_is_dir_or_absent
  mkdir -p "$(dirname "$DEST")"
  blue "Copie rsync vers $DEST (première fois : long ; OneDrive peut ralentir)…"
  rsync -avh --progress "${SOURCE}/" "${DEST}/"
  green "Copie terminée."
}

cmd_verify() {
  need_src
  if [ ! -d "$DEST" ]; then
    red "DEST introuvable : $DEST — lance d’abord : copy"
    exit 1
  fi
  blue "Vérification dry-run (--itemize-changes, aucune écriture)…"
  yellow "Note : rsync peut parfois signaler de petites différences de métadonnées sans impact fonctionnel ; en revanche, beaucoup de lignes commençant par « > » sur de vrais fichiers → relance copy ou inspecte."
  local tmp
  tmp=$(mktemp)
  rsync -avh --dry-run --itemize-changes "${SOURCE}/" "${DEST}/" >"$tmp" 2>&1 || true
  if [ ! -s "$tmp" ]; then
    green "OK — rien à synchroniser (sortie rsync vide)."
    rm -f "$tmp"
    return 0
  fi
  if grep -qE '^[><*]' "$tmp" 2>/dev/null; then
    yellow "Des chemins itemisés encore en attente ; extrait (max 40 lignes) :"
    head -40 "$tmp"
    rm -f "$tmp"
    exit 1
  fi
  rm -f "$tmp"
  green "OK — pas de transfert itemisé type fichier (sortie sans lignes ^[><*])."
}

cmd_xattr() {
  if [ ! -d "$DEST" ]; then
    red "DEST introuvable : $DEST"
    exit 1
  fi
  blue "Nettoyage xattrs (hors fichiers sous .git/*)…"
  find "$DEST" ! -path '*/.git/*' -exec xattr -c {} + 2>/dev/null || true
  green "xattr terminé."
}

cmd_git_check() {
  if [ -d "$DEST/.git" ] || [ -f "$DEST/.git" ]; then
    blue "Vérification Git (git status)…"
    if ! command -v git >/dev/null 2>&1; then
      red "git n’est pas dans le PATH ; impossible de valider le dépôt."
      exit 1
    fi
    if ! git -C "$DEST" status; then
      red "Le dépôt copié ne répond pas correctement à git status."
      exit 1
    fi
    green "Git OK."
  else
    yellow "Pas de dépôt Git détecté dans DEST — vérifie la copie ou un worktree."
  fi
}

cmd_all() {
  cmd_copy
  cmd_verify
  blue "Tailles disque SOURCE vs DEST (réassurance, du -sh) :"
  du -sh "$SOURCE" "$DEST" 2>/dev/null || true
  echo
  cmd_xattr
  echo
  cmd_git_check
  echo
  green "Étapes suivantes (manuel) :"
  echo "  cd $DEST/services/arquantix/mobile && flutter clean && flutter pub get"
  echo "  cd ios && pod install && cd .."
  echo "  Ouvre Cursor sur $DEST ; terminal et builds uniquement là — plus rien d’opérationnel sur OneDrive tant que tu valides."
  echo "  Garde OneDrive comme backup jusqu’à validation."
}

case "${1:-}" in
  copy) cmd_copy ;;
  verify) cmd_verify ;;
  xattr) cmd_xattr ;;
  all) cmd_all ;;
  -h|--help|help) usage ;;
  *)
    red "Commande inconnue : ${1:-}"
    usage
    exit 1
    ;;
esac
