# shellcheck shell=bash
# Charge [.env.flutter] et prépare des --dart-define supplémentaires (Privy, etc.).
#
# Prérequis : la variable SCRIPT_DIR doit être définie (répertoire `mobile/`).
# Fichier : par défaut ${SCRIPT_DIR}/.env.flutter ; surcharge : ENV_FLUTTER_FILE=/chemin/.env.autre

: "${SCRIPT_DIR:?Définir SCRIPT_DIR avant de sourcer flutter_local_env.sh}"

FLUTTER_LOCAL_ENV_FILE="${ENV_FLUTTER_FILE:-${SCRIPT_DIR}/.env.flutter}"

if [[ -f "$FLUTTER_LOCAL_ENV_FILE" ]]; then
  echo "→ Charge ${FLUTTER_LOCAL_ENV_FILE#$SCRIPT_DIR/}"
  set -a
  # shellcheck disable=SC1090
  source "$FLUTTER_LOCAL_ENV_FILE"
  set +a
fi

# Toujours initialiser pour utilisation même sans fichier local.
FLUTTER_EXTRA_DART_DEFINES=()

if [[ -n "${PRIVY_APP_ID:-}" ]]; then
  FLUTTER_EXTRA_DART_DEFINES+=(--dart-define=PRIVY_APP_ID="$PRIVY_APP_ID")
fi
if [[ -n "${PRIVY_APP_CLIENT_ID:-}" ]]; then
  FLUTTER_EXTRA_DART_DEFINES+=(--dart-define=PRIVY_APP_CLIENT_ID="$PRIVY_APP_CLIENT_ID")
fi
if [[ -n "${PRIVY_OAUTH_SCHEME:-}" ]]; then
  FLUTTER_EXTRA_DART_DEFINES+=(--dart-define=PRIVY_OAUTH_SCHEME="$PRIVY_OAUTH_SCHEME")
fi
