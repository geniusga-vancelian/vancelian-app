#!/bin/bash
# Raccourci principal : lance l'émulateur + l'app Flutter Arquantix News
# Usage: ./go.sh   ou   arq   (si alias configuré)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export API_BASE_URL="${API_BASE_URL:-http://10.0.2.2:3000}"
exec ./run-android.sh "$@"
