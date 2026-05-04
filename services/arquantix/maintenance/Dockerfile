# Image maintenance Arquantix — nginx alpine, template envsubst au démarrage.
# Customisable sans rebuild via env vars (titre/sous-titre/eta) + retourne HTTP 503.
FROM nginx:1.27-alpine

RUN apk add --no-cache gettext ca-certificates

COPY conf/nginx.conf /etc/nginx/nginx.conf
COPY html/index.html.template /usr/share/nginx/templates/index.html.template
COPY html/logo.svg /usr/share/nginx/html/logo.svg
COPY html/favicon.ico /usr/share/nginx/html/favicon.ico

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENV PORT=8080 \
    MAINT_TITLE="Site en maintenance" \
    MAINT_SUBTITLE="Nous revenons très vite. Merci pour votre patience." \
    MAINT_ETA="" \
    MAINT_BRAND="Arquantix"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
