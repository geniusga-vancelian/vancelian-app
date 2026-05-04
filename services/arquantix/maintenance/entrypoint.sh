#!/bin/sh
set -eu

# Templating index.html depuis les env vars (sans rebuild image).
TEMPLATE=/usr/share/nginx/templates/index.html.template
TARGET=/usr/share/nginx/html/index.html

# Variables exposées dans le template (échappées HTML par envsubst — basique).
export MAINT_TITLE="${MAINT_TITLE:-Site en maintenance}"
export MAINT_SUBTITLE="${MAINT_SUBTITLE:-Nous revenons très vite.}"
export MAINT_ETA="${MAINT_ETA:-}"
export MAINT_BRAND="${MAINT_BRAND:-Arquantix}"
export PORT="${PORT:-8080}"

# Render index.html.
envsubst '${MAINT_TITLE} ${MAINT_SUBTITLE} ${MAINT_ETA} ${MAINT_BRAND}' < "$TEMPLATE" > "$TARGET"

# Render nginx.conf : on substitue uniquement ${PORT} pour permettre l'override par ECS.
NGINX_CONF=/etc/nginx/nginx.conf
NGINX_TPL=/etc/nginx/nginx.conf.tpl
if [ ! -f "$NGINX_TPL" ]; then
  cp "$NGINX_CONF" "$NGINX_TPL"
fi
envsubst '${PORT}' < "$NGINX_TPL" > "$NGINX_CONF"

echo "[maintenance] Rendered template (PORT=$PORT, BRAND=$MAINT_BRAND)"
echo "[maintenance] Title:    $MAINT_TITLE"
echo "[maintenance] Subtitle: $MAINT_SUBTITLE"
[ -n "$MAINT_ETA" ] && echo "[maintenance] ETA:      $MAINT_ETA"

exec "$@"
