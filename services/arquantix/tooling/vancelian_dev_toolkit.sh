#!/bin/bash
# Boîte à outils dev locale (sync ~/dev, Flutter, API, Web, Xcode, iPhone).
# Emplacement attendu : services/arquantix/tooling/ (parent = racine arquantix : mobile/, api/, web/).
#
# Hot reload : dans le menu → 16) flutter attach ; ou en CLI : ./vancelian_dev_toolkit.sh attach
# (app déjà lancée en debug sur le device ; puis r = reload, R = restart dans le terminal attaché).
# Lancement debug explicite : menu 17) / 18) ou CLI : ./vancelian_dev_toolkit.sh debug | clean-debug
#
# Surcharges : DEVICE_ID, SOURCE_MOBILE, SOURCE_API, SOURCE_WEB, LOCAL_DEV_ROOT, LOCAL_MOBILE
# SKIP_GIT_PULL=1 — ne pas faire git pull au lancement / avant fast|clean|release
# SKIP_AUTO_DEVICE=1 — utiliser uniquement DEVICE_ID (sans vérifier flutter ; comportement direct)
# PREFER_WIRELESS=1 — en cas d’ambiguïté, préférer un iPhone wireless
# PREFER_USB=1 — en cas d’ambiguïté, préférer un iPhone USB
# DEVICE_ID_DEFAULT — UDID « préféré » (tie-break si plusieurs devices, pas un forçage silencieux)
#
# VM Service / « Connection refused » en Wi‑Fi (iPhone sans fil) :
#   • USB souvent plus fiable ; ou USE_FLUTTER_DEBUG=1 avant le menu (lance en debug au lieu de profile)
#   • ou FLUTTER_NO_DDS=1 (ajoute --no-dds) ; ou FLUTTER_RUN_EXTRA_ARGS='--host-vmservice-port 0' (surcharges)
#   • ou lancer depuis Xcode puis menu 16) flutter attach
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Parent de tooling/ = services/arquantix
ARQUANTIX_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GIT_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"

# Préférence locale optionnelle (tie-break) ; ne remplace pas la sélection smart si non connecté
DEVICE_ID_DEFAULT="${DEVICE_ID_DEFAULT:-00008130-001165803A88001C}"
SOURCE_MOBILE_DEFAULT="$ARQUANTIX_ROOT/mobile"
SOURCE_API_DEFAULT="$ARQUANTIX_ROOT/api"
SOURCE_WEB_DEFAULT="$ARQUANTIX_ROOT/web"
LOCAL_DEV_ROOT_DEFAULT="$HOME/dev"
LOCAL_MOBILE_DEFAULT="$LOCAL_DEV_ROOT_DEFAULT/vancelian-mobile"

# DEVICE_ID : si défini dans l’environnement (même vide), on respecte ; sinon logique smart sans forçage
if [ -z "${DEVICE_ID+x}" ]; then
  USER_DEVICE_ID=""
else
  USER_DEVICE_ID="${DEVICE_ID:-}"
fi

SOURCE_MOBILE="${SOURCE_MOBILE:-$SOURCE_MOBILE_DEFAULT}"
SOURCE_API="${SOURCE_API:-$SOURCE_API_DEFAULT}"
SOURCE_WEB="${SOURCE_WEB:-$SOURCE_WEB_DEFAULT}"
LOCAL_DEV_ROOT="${LOCAL_DEV_ROOT:-$LOCAL_DEV_ROOT_DEFAULT}"
LOCAL_MOBILE="${LOCAL_MOBILE:-$LOCAL_MOBILE_DEFAULT}"

blue() { printf "\033[1;34m%s\033[0m\n" "$*"; }
green() { printf "\033[1;32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[1;33m%s\033[0m\n" "$*"; }
red() { printf "\033[1;31m%s\033[0m\n" "$*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { red "Missing command: $1"; exit 1; }
}

# Met à jour le dépôt (racine monorepo) pour récupérer les derniers commits sans action manuelle.
git_pull_latest() {
  if [ -n "${SKIP_GIT_PULL:-}" ]; then
    yellow "Git pull ignoré (SKIP_GIT_PULL défini)."
    return 0
  fi
  if [ -z "${GIT_ROOT:-}" ]; then
    yellow "Pas de dépôt git détecté depuis ce script ; pull ignoré."
    return 0
  fi
  blue "Mise à jour du dépôt : $GIT_ROOT"
  if git -C "$GIT_ROOT" pull --ff-only 2>&1; then
    green "OK — branche $(git -C "$GIT_ROOT" rev-parse --abbrev-ref HEAD) @ $(git -C "$GIT_ROOT" rev-parse --short HEAD)"
  else
    yellow "git pull a échoué (hors ligne, conflits, ou branche non suivie). Tu peux continuer quand même."
  fi
}

# --- Détection / classification devices (flutter devices --machine + heuristiques) ---
# Sortie stdout : une ligne JSON compacte avec clés usb, wireless, simulator (tableaux de {id,name})
# ou ligne spéciale RESOLVED|<udid> si déjà choisi automatiquement
# Sortie : ligne « RESOLVED|<udid> » ou JSON (stdout uniquement ; ne pas s’appuyer sur le code de sortie dans $(...)).
export DEVICE_ID_DEFAULT
export USER_DEVICE_ID
export PREFER_WIRELESS="${PREFER_WIRELESS:-}"
export PREFER_USB="${PREFER_USB:-}"

_flutter_classify_and_resolve() {
  need_cmd python3
  need_cmd flutter
  local machine_json outf code
  machine_json="$(flutter devices --machine 2>/dev/null || true)"
  if [ -z "$machine_json" ]; then
    red "flutter devices --machine n’a rien retourné." >&2
    return 1
  fi
  outf=$(mktemp)
  _TK_MACHINE_JSON="$machine_json" USER_DEVICE_ID="$USER_DEVICE_ID" DEVICE_ID_DEFAULT="$DEVICE_ID_DEFAULT" \
    PREFER_WIRELESS="${PREFER_WIRELESS:-}" PREFER_USB="${PREFER_USB:-}" \
    python3 - <<'PY' >"$outf" || { rm -f "$outf"; return 1; }
import json, os, re, subprocess, sys

def flutter_text_wireless_udids():
    try:
        out = subprocess.run(
            ["flutter", "devices"],
            capture_output=True, text=True, timeout=120,
        ).stdout
    except Exception:
        return set()
    found = set()
    for line in out.splitlines():
        low = line.lower()
        if "wireless" not in low:
            continue
        # ex. "iPhone (wireless) (mobile) • 00008130-... • ios"
        for m in re.finditer(r"•\s*([0-9A-Fa-f]{8}-[0-9A-Fa-f-]+)\s*•", line):
            found.add(m.group(1))
    return found

def xcdevice_iface_by_udid():
    """Optionnel : interface Apple pour iPhone physiques (usb / wifi / …)."""
    try:
        raw = subprocess.run(
            ["xcrun", "xcdevice", "list"],
            capture_output=True, text=True, timeout=45,
        ).stdout
        data = json.loads(raw)
    except Exception:
        return {}
    out = {}
    for d in data:
        if d.get("simulator") or d.get("platform") != "com.apple.platform.iphoneos":
            continue
        if not d.get("available", True):
            continue
        ident = d.get("identifier")
        if not ident:
            continue
        iface = (d.get("interface") or "").lower()
        out[ident] = iface
    return out

def is_ios_simulator(d):
    if d.get("emulator") is True:
        return True
    did = (d.get("id") or "").lower()
    name = d.get("name") or ""
    if "simulator" in did or "iphonesimulator" in did:
        return True
    if "simulator" in name.lower():
        return True
    return False

def is_junk(d):
    tid = (d.get("id") or "").strip()
    if tid in ("chrome", "web-server", "edge"):
        return True
    tp = d.get("targetPlatform") or ""
    if tp in ("web-javascript", "darwin", "macos", "linux", "windows"):
        return True
    return False

def main():
    raw = os.environ.get("_TK_MACHINE_JSON") or ""
    if not raw:
        raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}", flush=True)
        sys.exit(0)

    wireless_text = flutter_text_wireless_udids()
    xc_if = xcdevice_iface_by_udid()

    usb, wireless, sims = [], [], []

    for d in data:
        if is_junk(d):
            continue
        if d.get("targetPlatform") != "ios":
            continue
        if not d.get("isSupported", True):
            continue
        did = d.get("id") or ""
        name = d.get("name") or "iOS"
        if not did:
            continue

        if is_ios_simulator(d):
            sims.append({"id": did, "name": name})
            continue

        # Physique iOS — USB vs wireless (Flutter --machine est souvent pauvre ; on combine texte + xcdevice)
        name_l = name.lower()
        conn = (d.get("connectionInterface") or d.get("connection") or "").lower()
        xc = (xc_if.get(did) or "").lower()
        is_w = (
            did in wireless_text
            or "wireless" in name_l
            or conn == "wireless"
            or xc == "wifi"
        )
        is_u = conn in ("usb", "attached", "wired") or xc == "usb"
        if is_w and not is_u:
            wireless.append({"id": did, "name": name})
        elif is_u and not is_w:
            usb.append({"id": did, "name": name})
        elif is_w and is_u:
            # rare : privilégier le flag explicite flutter devices (texte)
            if did in wireless_text:
                wireless.append({"id": did, "name": name})
            else:
                usb.append({"id": did, "name": name})
        else:
            if did in wireless_text or "wireless" in name_l:
                wireless.append({"id": did, "name": name})
            else:
                usb.append({"id": did, "name": name})

    user = (os.environ.get("USER_DEVICE_ID") or "").strip()
    pref = (os.environ.get("DEVICE_ID_DEFAULT") or "").strip()
    prefer_w = os.environ.get("PREFER_WIRELESS", "").strip() in ("1", "true", "yes")
    prefer_u = os.environ.get("PREFER_USB", "").strip() in ("1", "true", "yes")

    physical = usb + wireless

    # 1) USER_DEVICE_ID explicite : doit exister dans la liste flutter
    if user:
        for bucket in (usb, wireless, sims):
            for x in bucket:
                if x["id"] == user:
                    print(f"RESOLVED|{user}", flush=True)
                    sys.exit(0)
        # non trouvé → laissera le menu / aide
        print(json.dumps({"usb": usb, "wireless": wireless, "simulator": sims, "requested_missing": user}), flush=True)
        sys.exit(0)

    # 2) Un seul physique
    if len(physical) == 1:
        print(f"RESOLVED|{physical[0]['id']}", flush=True)
        sys.exit(0)

    # 3) Plusieurs physiques : tie-break préférence
    if len(physical) > 1 and pref:
        for bucket in (usb, wireless):
            for x in bucket:
                if x["id"] == pref:
                    print(f"RESOLVED|{x['id']}", flush=True)
                    sys.exit(0)

    if len(physical) > 1:
        if prefer_w and wireless:
            print(f"RESOLVED|{wireless[0]['id']}", flush=True)
            sys.exit(0)
        if prefer_u and usb:
            print(f"RESOLVED|{usb[0]['id']}", flush=True)
            sys.exit(0)

    # Aucun iPhone physique : simulateurs seulement
    if not physical and sims:
        if len(sims) == 1:
            print(f"RESOLVED|{sims[0]['id']}", flush=True)
            sys.exit(0)
        print(json.dumps({"usb": [], "wireless": [], "simulator": sims}), flush=True)
        sys.exit(0)

    print(json.dumps({"usb": usb, "wireless": wireless, "simulator": sims}), flush=True)
    sys.exit(0)

if __name__ == "__main__":
    main()
PY
  cat "$outf"
  rm -f "$outf"
  return 0
}

resolve_flutter_device() {
  if [ -n "${SKIP_AUTO_DEVICE:-}" ]; then
    if [ -n "${USER_DEVICE_ID:-}" ]; then
      echo "$USER_DEVICE_ID"
    else
      red "SKIP_AUTO_DEVICE : définis DEVICE_ID (export DEVICE_ID=...)."
      return 1
    fi
    return 0
  fi

  local out resolved json miss
  out="$(_flutter_classify_and_resolve)" || { red "Échec détection Flutter." >&2; return 1; }

  if [[ "$out" == RESOLVED\|* ]]; then
    resolved="${out#RESOLVED|}"
    resolved="${resolved//$'\r'/}"
    resolved="${resolved//$'\n'/}"
    green "Cible Flutter : $resolved" >&2
    echo "$resolved"
    return 0
  fi

  json="$out"
  if [ -z "$json" ] || [ "$json" = "{}" ]; then
    _device_assist_menu "empty"
    return 1
  fi

  miss="$(echo "$json" | python3 -c "import json,sys; print(json.load(sys.stdin).get('requested_missing') or '')" 2>/dev/null || true)"
  if [ -n "$miss" ]; then
    yellow "DEVICE_ID demandé ($miss) absent de la liste Flutter — choisis une cible ci-dessous." >&2
  fi

  _interactive_device_pick "$json"
}

_interactive_device_pick() {
  local json="$1"
  need_cmd python3
  local -a lines ids
  lines=()
  ids=()

  # Bash 3.2 (macOS) n'a pas mapfile — remplir lines[] avec read.
  while IFS= read -r line || [ -n "$line" ]; do
    lines+=("$line")
  done < <(export _TK_JSON="$json"; python3 <<'PY'
import json, os
j = json.loads(os.environ["_TK_JSON"])
usb, w, sims = j.get("usb") or [], j.get("wireless") or [], j.get("simulator") or []
for label, bucket in (
    ("iPhone USB", usb),
    ("iPhone wireless", w),
    ("simulateur iOS", sims),
):
    for d in bucket:
        print(f"{label}\t{d['name']}\t{d['id']}")
PY
)

  if [ "${#lines[@]}" -eq 0 ]; then
    _device_assist_menu "empty"
    return 1
  fi

  echo "" >&2
  blue "──────── Sélection du device Flutter ────────" >&2
  local n=0
  for line in "${lines[@]}"; do
    n=$((n + 1))
    IFS=$'\t' read -r kind name udid <<<"$line"
    echo "  $n) Utiliser $kind — $name — $udid" >&2
    ids+=("$udid")
  done
  local xcode_choice=$((n + 1))
  local cancel_choice=$((n + 2))
  echo "  $xcode_choice) Ouvrir Xcode (Runner.xcworkspace)" >&2
  echo "  $cancel_choice) Annuler" >&2
  echo "" >&2
  read -r -p "Choix [1-$cancel_choice] : " pick

  if [ "$pick" = "$xcode_choice" ]; then
    _open_xcode_workspace_help
    return 1
  fi
  if [ "$pick" = "$cancel_choice" ] || [ "$pick" = "q" ] || [ "$pick" = "Q" ]; then
    yellow "Annulé." >&2
    return 1
  fi
  if ! [[ "$pick" =~ ^[0-9]+$ ]] || [ "$pick" -lt 1 ] || [ "$pick" -gt "$n" ]; then
    red "Choix invalide." >&2
    return 1
  fi
  green "Device sélectionné : ${ids[$((pick - 1))]}" >&2
  echo "${ids[$((pick - 1))]}"
  return 0
}

_device_assist_menu() {
  local reason="${1:-}"
  local missing="${2:-}"
  echo "" >&2
  yellow "Aucune cible Flutter prête (ou liste vide)." >&2
  if [ -n "$missing" ]; then
    yellow "DEVICE_ID demandé : $missing" >&2
  fi
  echo "" >&2
  echo "  1) Ouvrir Xcode + rappels (USB, confiance, mode développeur)" >&2
  echo "  2) Afficher flutter devices" >&2
  echo "  3) Annuler" >&2
  read -r -p "Choix : " a
  case "$a" in
    1) _open_xcode_workspace_help ;;
    2) flutter devices >&2 ;;
    *) yellow "OK." >&2 ;;
  esac
  return 1
}

_open_xcode_workspace_help() {
  ensure_local_copy
  blue "Ouverture de Runner.xcworkspace…"
  open "$LOCAL_MOBILE/ios/Runner.xcworkspace" 2>/dev/null || true
  green "Xcode ouvert."
  echo ""
  yellow "Checklist rapide :"
  echo "  • Branche l’iPhone en USB ou active la paire sans fil (même réseau Wi‑Fi)."
  echo "  • Déverrouille l’iPhone ; accepte « Faire confiance à cet ordinateur »."
  echo "  • Réglages > Confidentialité et sécurité > Mode développeur (si demandé)."
  echo "  • Xcode : Window > Devices and Simulators — vérifie que l’appareil est « ready »."
  echo "  • Puis : flutter devices   ou   relance ce script."
  echo ""
}

bootstrap_session() {
  git_pull_latest
}

get_ip() {
  local ip
  ip=$(ipconfig getifaddr en0 2>/dev/null || true)
  if [ -z "${ip}" ]; then
    ip=$(ipconfig getifaddr en1 2>/dev/null || true)
  fi
  echo "${ip}"
}

ensure_local_copy() {
  mkdir -p "$LOCAL_DEV_ROOT"
  blue "Syncing mobile app to local dev folder..."
  rsync -a --delete "$SOURCE_MOBILE/" "$LOCAL_MOBILE/"
  # Retire les xattrs (ex. quarantine OneDrive) sans toucher aux fichiers sous .git (souvent 0444 → Permission denied).
  find "$LOCAL_MOBILE" ! -path '*/.git/*' -exec xattr -c {} + 2>/dev/null || true
  green "Local mobile copy ready: $LOCAL_MOBILE"
}

clean_mobile_ios() {
  cd "$LOCAL_MOBILE"
  blue "Flutter clean..."
  flutter clean
  blue "Flutter pub get..."
  flutter pub get
  cd ios
  blue "Resetting CocoaPods..."
  rm -rf Pods Podfile.lock .symlinks
  pod install
  cd ..
  green "Flutter + CocoaPods reset complete."
}

kill_flutter_and_xcodebuild() {
  blue "Killing flutter/xcodebuild if running..."
  pkill -f "flutter run" 2>/dev/null || true
  pkill -f xcodebuild 2>/dev/null || true
  green "Processes cleared."
}

# Python pour l’API : venv local en priorité, sinon python3 du PATH.
resolve_api_python() {
  local d="$SOURCE_API"
  if [ -x "$d/.venv/bin/python" ]; then
    echo "$d/.venv/bin/python"
    return 0
  fi
  if [ -x "$d/.venv/bin/python3" ]; then
    echo "$d/.venv/bin/python3"
    return 0
  fi
  if [ -x "$d/venv/bin/python" ]; then
    echo "$d/venv/bin/python"
    return 0
  fi
  if [ -x "$d/venv/bin/python3" ]; then
    echo "$d/venv/bin/python3"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  return 1
}

start_api() {
  local py
  if ! py="$(resolve_api_python)"; then
    red "Aucun interpréteur Python trouvé (installe python3 ou crée $SOURCE_API/.venv)."
    return 1
  fi
  if ! "$py" -c "import uvicorn" 2>/dev/null; then
    red "Le module Python « uvicorn » n’est pas disponible pour : $py"
    red "Exemple : cd \"$SOURCE_API\" && \"$py\" -m pip install -r requirements.txt"
    return 1
  fi
  cd "$SOURCE_API"
  blue "Starting FastAPI on 0.0.0.0:8000 (python: $py, python -m uvicorn) …"
  nohup "$py" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "$LOCAL_DEV_ROOT/api.log" 2>&1 &
  sleep 2
  green "FastAPI started. Log: $LOCAL_DEV_ROOT/api.log"
}

start_web() {
  need_cmd npm
  cd "$SOURCE_WEB"
  blue "Starting Next/BFF on 0.0.0.0:3000 ..."
  nohup npm run dev -- --hostname 0.0.0.0 --port 3000 > "$LOCAL_DEV_ROOT/web.log" 2>&1 &
  sleep 3
  green "Web/BFF started. Log: $LOCAL_DEV_ROOT/web.log"
}

stop_servers() {
  blue "Stopping uvicorn / next node dev servers..."
  # Couvre « uvicorn … » et « python -m uvicorn … »
  pkill -f "uvicorn main:app" 2>/dev/null || true
  pkill -f "next dev" 2>/dev/null || true
  green "Servers stopped."
}

show_status() {
  local ip
  ip=$(get_ip)
  blue "===== STATUS ====="
  echo "IP: ${ip:-NOT FOUND}"
  if [ -z "${DEVICE_ID+x}" ]; then
    echo "DEVICE_ID (env) : (non défini — sélection smart)"
  else
    echo "DEVICE_ID (env) : ${DEVICE_ID:-<vide>}"
  fi
  echo "USER_DEVICE_ID (résolu) : ${USER_DEVICE_ID:-<vide>}"
  echo "DEVICE_ID_DEFAULT (tie-break si plusieurs devices) : $DEVICE_ID_DEFAULT"
  echo "Git repo root: ${GIT_ROOT:-non détecté}"
  echo "Local mobile: $LOCAL_MOBILE"
  echo "Arquantix root: $ARQUANTIX_ROOT"
  echo
  yellow "flutter devices (extrait) :"
  flutter devices 2>/dev/null | head -40 || true
  echo
  yellow "Listening ports:"
  lsof -iTCP:8000 -sTCP:LISTEN -n -P || true
  lsof -iTCP:3000 -sTCP:LISTEN -n -P || true
  echo
  yellow "Health checks:"
  if [ -n "${ip}" ]; then
    curl -s "http://${ip}:8000/health" || true
    echo
    curl -I -s "http://${ip}:3000" | head -n 5 || true
  else
    echo "No local IP detected."
  fi
  echo
  yellow "Stack BFF + DB (profil mobile, Postgres) :"
  if [ -x "$ARQUANTIX_ROOT/tooling/check_arquantix_dev_stack.sh" ]; then
    bash "$ARQUANTIX_ROOT/tooling/check_arquantix_dev_stack.sh" || true
  else
    echo "  (script absent : $ARQUANTIX_ROOT/tooling/check_arquantix_dev_stack.sh)"
  fi
  echo
}

open_workspace() {
  ensure_local_copy
  open "$LOCAL_MOBILE/ios/Runner.xcworkspace"
  green "Opened Runner.xcworkspace"
}

reset_xcode_ios_state() {
  blue "Resetting Xcode DeviceSupport and DerivedData..."
  rm -rf "$HOME/Library/Developer/Xcode/iOS DeviceSupport/"*
  rm -rf "$HOME/Library/Developer/Xcode/DerivedData/"*
  green "Xcode caches reset."
}

# Attache le CLI Flutter à une app déjà lancée (debug) sur le device : r = Hot Reload, R = Hot Restart.
# Prérequis : `flutter run` / fast launch en cours sur ce device (même projet).
flutter_hot_attach() {
  local resolved
  need_cmd flutter
  need_cmd python3
  ensure_local_copy
  blue "Sélection du device (même logique que Fast launch)…"
  if ! resolved="$(resolve_flutter_device)"; then
    red "Arrêt : aucune cible Flutter."
    return 1
  fi
  yellow "Prérequis : l’app doit déjà tourner sur ce device en mode debug (ex. menu 17) ou fast avec USE_FLUTTER_DEBUG=1."
  echo ""
  blue "Une fois attaché, dans ce terminal :"
  echo "  • r puis Entrée  → Hot reload (rapide, garde l’état)"
  echo "  • R puis Entrée  → Hot restart (recharge tout le code Dart)"
  echo "  • h             → aide Flutter"
  echo "  • q puis Entrée  → quitter l’attach (l’app reste sur le téléphone)"
  echo ""
  cd "$LOCAL_MOBILE"
  blue "flutter attach -d $resolved"
  flutter attach -d "$resolved"
}

run_flutter() {
  local mode="${1:-profile}"
  local ip resolved
  need_cmd flutter
  need_cmd python3
  blue "Étape 1/3 : adresse IP du Mac (Wi‑Fi)…"
  ip=$(get_ip)
  if [ -z "${ip}" ]; then
    red "Impossible de détecter l’IP (Wi‑Fi). Connecte le Mac au Wi‑Fi puis réessaie."
    exit 1
  fi
  blue "Étape 2/3 : sélection du device iOS (USB / wireless / simulateur)…"
  if ! resolved="$(resolve_flutter_device)"; then
    red "Arrêt : aucune cible Flutter sélectionnée."
    exit 1
  fi
  if [ -z "${resolved}" ]; then
    red "Arrêt : appareil introuvable."
    exit 1
  fi
  blue "Étape 3/3 : flutter run (build + install ; Ctrl+C pour arrêter)…"
  cd "$LOCAL_MOBILE"
  # Même logique que services/arquantix/mobile/scripts/flutter_local_env.sh :
  # charge ${LOCAL_MOBILE}/.env.flutter et prépare FLUTTER_EXTRA_DART_DEFINES (Privy, etc.).
  if [[ -f "$LOCAL_MOBILE/scripts/flutter_local_env.sh" ]]; then
    SCRIPT_DIR="$LOCAL_MOBILE"
    # shellcheck source=/dev/null
    source "$LOCAL_MOBILE/scripts/flutter_local_env.sh"
  else
    yellow "Attention : scripts/flutter_local_env.sh introuvable sous $LOCAL_MOBILE — defines Privy non chargés."
    FLUTTER_EXTRA_DART_DEFINES=()
  fi
  local run_mode="$mode"
  if [ "${USE_FLUTTER_DEBUG:-}" = "1" ] && [ "$mode" = "profile" ]; then
    run_mode="debug"
    yellow "USE_FLUTTER_DEBUG=1 → lancement en **debug** (VM Service plus fiable qu’en profile sur certains iPhone Wi‑Fi)."
  fi
  local extra="${FLUTTER_RUN_EXTRA_ARGS:-}"
  if [ "${FLUTTER_NO_DDS:-}" = "1" ]; then
    extra="$extra --no-dds"
    yellow "FLUTTER_NO_DDS=1 → --no-dds (contourne parfois l’échec de connexion VM Service en Wi‑Fi)."
  fi
  yellow "Si « VM Service / Connection refused » persiste : branchez l’iPhone en USB, ou relancez avec USE_FLUTTER_DEBUG=1, ou menu 16) flutter attach après Run depuis Xcode."
  blue "Lancement Flutter ($run_mode) sur $resolved — IP $ip"
  # shellcheck disable=SC2086
  flutter run --"$run_mode" -d "$resolved" \
    --dart-define=FLAVOR=dev \
    --dart-define=API_BASE_URL="http://${ip}:3000" \
    --dart-define=AUTH_API_BASE_URL="http://${ip}:8000" \
    --dart-define=TRACE_JANK=true \
    "${FLUTTER_EXTRA_DART_DEFINES[@]}" \
    $extra
}

quick_boot() {
  ensure_local_copy
  open_workspace
  green "Quick boot ready."
}

full_clean_launch() {
  ensure_local_copy
  kill_flutter_and_xcodebuild
  clean_mobile_ios
  open_workspace
  run_flutter profile
}

fast_launch() {
  ensure_local_copy
  kill_flutter_and_xcodebuild
  run_flutter profile
}

fast_launch_debug() {
  ensure_local_copy
  kill_flutter_and_xcodebuild
  run_flutter debug
}

full_clean_launch_debug() {
  ensure_local_copy
  kill_flutter_and_xcodebuild
  clean_mobile_ios
  open_workspace
  run_flutter debug
}

network_test() {
  local ip
  ip=$(get_ip)
  blue "Detected IP: ${ip:-NOT FOUND}"
  if [ -z "${ip}" ]; then
    red "No IP found."
    return 1
  fi
  echo
  blue "Run these on iPhone Safari:"
  echo "http://${ip}:8000/health"
  echo "http://${ip}:3000"
  echo
  blue "Mac-side curls:"
  curl "http://127.0.0.1:8000/health" || true
  echo
  curl "http://${ip}:8000/health" || true
  echo
  curl -I "http://${ip}:3000" | head -n 5 || true
}

print_menu() {
  cat <<EOF

================ VANCELIAN DEV TOOLKIT ================
0) Git pull maintenant (aussi au lancement du menu)
1) Sync mobile app locally
2) Clean Flutter + Pods
3) Start FastAPI server
4) Start Web / Next server
5) Stop API + Web servers
6) Open Xcode workspace
7) Reset Xcode iPhone caches
8) Show status + health checks
9) Network test helper
10) Fast launch (profile) — sélection device smart  [Wi‑Fi bloqué ? USE_FLUTTER_DEBUG=1 ./…]
11) Full clean + launch (profile) — sélection device smart  [idem]
12) Launch release — sélection device smart
13) Kill flutter/xcodebuild
14) Quick boot (sync + open Xcode)
15) Choisir / tester la détection device (flutter devices)
16) Hot reload / Hot restart — flutter attach (app déjà lancée en debug)
17) Fast launch (debug) — sélection device smart  [VM Service / hot reload natifs]
18) Full clean + launch (debug) — sélection device smart  [idem]
q) Quit
=======================================================
EOF
}

main_menu() {
  need_cmd flutter
  need_cmd rsync
  need_cmd pod
  bootstrap_session
  while true; do
    print_menu
    read -r -p "Choose an option: " choice
    case "$choice" in
      0) git_pull_latest ;;
      1) ensure_local_copy ;;
      2) ensure_local_copy; clean_mobile_ios ;;
      3) start_api ;;
      4) start_web ;;
      5) stop_servers ;;
      6) open_workspace ;;
      7) reset_xcode_ios_state ;;
      8) show_status ;;
      9) network_test ;;
      10) fast_launch ;;
      11) full_clean_launch ;;
      12) ensure_local_copy; kill_flutter_and_xcodebuild; run_flutter release ;;
      13) kill_flutter_and_xcodebuild ;;
      14) quick_boot ;;
      15) blue "flutter devices"; flutter devices; echo; blue "flutter devices --machine (résumé)"; flutter devices --machine | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d),'device(s) JSON')" 2>/dev/null || true ;;
      16) flutter_hot_attach ;;
      17) fast_launch_debug ;;
      18) full_clean_launch_debug ;;
      q|Q) green "Bye."; exit 0 ;;
      *) yellow "Invalid option." ;;
    esac
    echo
  done
}

case "${1:-}" in
  menu|"") main_menu ;;
  pull) git_pull_latest ;;
  fast) bootstrap_session; fast_launch ;;
  clean) bootstrap_session; full_clean_launch ;;
  debug|fast-debug) bootstrap_session; fast_launch_debug ;;
  clean-debug) bootstrap_session; full_clean_launch_debug ;;
  release) bootstrap_session; ensure_local_copy; kill_flutter_and_xcodebuild; run_flutter release ;;
  api) start_api ;;
  web) start_web ;;
  stop) stop_servers ;;
  status) show_status ;;
  xcode) open_workspace ;;
  net) network_test ;;
  reset-xcode) reset_xcode_ios_state ;;
  devices) flutter devices; echo; flutter devices --machine | python3 -m json.tool 2>/dev/null | head -120 ;;
  attach|hot|hot-attach) ensure_local_copy; flutter_hot_attach ;;
  *)
    red "Unknown command: ${1}"
    echo "Usage: $0 [menu|pull|fast|clean|debug|fast-debug|clean-debug|release|api|web|stop|status|xcode|net|reset-xcode|devices|attach]"
    exit 1
    ;;
esac
