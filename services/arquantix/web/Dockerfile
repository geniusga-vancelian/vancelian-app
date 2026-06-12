# --- deps ---
FROM node:20-alpine AS deps
# libc6-compat : résolution binaire Prisma sur musl — ca-certificates : TLS fiables pour npm / téléchargement engines
# python3 + build-base : node-gyp (bufferutil, etc.) lors de npm ci
RUN apk add --no-cache libc6-compat ca-certificates python3 make g++
WORKDIR /app
# Contexte de build = racine monorepo (CI / compose recovery).
COPY services/arquantix/web/package*.json ./
COPY services/arquantix/web/prisma ./prisma
# postinstall @prisma/engines = téléchargement binaires — ECONNRESET fréquent en CI / VPN : reprises + retry npm
RUN npm config set fetch-retries 7 \
  && npm config set fetch-retry-mintimeout 20000 \
  && npm config set fetch-retry-maxtimeout 120000 \
  && npm config set fetch-timeout 300000 \
  && for i in 1 2 3; do \
       npm ci && exit 0; \
       echo "[deps] npm ci a échoué (tentative $i/3), nouvel essai dans 8s…" >&2; \
       sleep 8; \
     done; \
     echo "[deps] npm ci impossible — repli npm install" >&2; \
     npm install

# --- build ---
FROM node:20-alpine AS builder
WORKDIR /app
ENV NODE_OPTIONS=--max-old-space-size=4096
COPY --from=deps /app/node_modules ./node_modules
COPY services/arquantix/web/ .
# public/crypto_svgs est un symlink git vers mobile/ — non résolu dans l'image Docker.
RUN rm -rf ./public/crypto_svgs
COPY services/arquantix/mobile/assets/crypto_svgs/ ./public/crypto_svgs/
ARG NEXT_PUBLIC_GIT_SHA
ENV NEXT_PUBLIC_GIT_SHA=$NEXT_PUBLIC_GIT_SHA
# Aligné avec l’API FastAPI (PORT=8000 par défaut) — doit être cohérent au moment du build (client bundle)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL
ARG NEXT_PUBLIC_SITE_URL=
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_PORTAL_APP_URL=
ENV NEXT_PUBLIC_PORTAL_APP_URL=$NEXT_PUBLIC_PORTAL_APP_URL
ARG NEXT_PUBLIC_PRIVY_APP_ID=
ENV NEXT_PUBLIC_PRIVY_APP_ID=$NEXT_PUBLIC_PRIVY_APP_ID
ARG NEXT_PUBLIC_PRIVY_AUTHORIZATION_QUORUM_ID=
ENV NEXT_PUBLIC_PRIVY_AUTHORIZATION_QUORUM_ID=$NEXT_PUBLIC_PRIVY_AUTHORIZATION_QUORUM_ID
ARG NEXT_PUBLIC_BASE_RPC_URL=
ENV NEXT_PUBLIC_BASE_RPC_URL=$NEXT_PUBLIC_BASE_RPC_URL
ARG NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=
ENV NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=$NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID
ARG NEXT_PUBLIC_ADMIN_LOGIN0_BG_VIDEO=
ENV NEXT_PUBLIC_ADMIN_LOGIN0_BG_VIDEO=$NEXT_PUBLIC_ADMIN_LOGIN0_BG_VIDEO
ARG NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED=
ENV NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED=$NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED
ARG NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE=
ENV NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE=$NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE
# Collecte des données de route au build : les handlers importent le client OpenAI
ENV OPENAI_API_KEY=sk-build-placeholder
# Après le tree complet, régénérer le client Prisma (évite un @prisma/client
# dérivé du seul `COPY prisma` de l’étape deps si le schéma a divergé en CI).
RUN npx prisma generate
RUN npm run build

# --- runner ---
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy production artifacts
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/next.config.js* ./
COPY --from=builder /app/public ./public
# Migrations : nécessaire pour `prisma migrate deploy` au démarrage (enum ArticleBlockType, etc. sur arquantix_fresh).
COPY --from=builder /app/prisma ./prisma
# Jobs Morpho one-shot / cron ECS (tsx scripts → src/lib).
COPY --from=builder /app/scripts ./scripts
COPY --from=builder /app/src ./src
COPY --from=builder /app/tsconfig.json ./tsconfig.json

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV HOST="0.0.0.0"
ENV PATH="/app/node_modules/.bin:$PATH"

# Applique d’abord les migrations (base Docker souvent en retard vs schéma Prisma), puis Next.
# Sans cela, l’image rebuild ne met pas à jour l’enum PG si personne n’a lancé migrate sur arquantix_fresh.
# En prod ECS, mettre RUN_PRISMA_MIGRATE_ON_START=0 si migrate deploy échoue (ex. P3005 : base non
# vide / baseline Prisma à faire à part) — le conteneur ne doit pas rester en crash-loop.
CMD ["sh", "-c", "set -e; if [ \"${RUN_PRISMA_MIGRATE_ON_START:-1}\" != \"0\" ]; then npx prisma migrate deploy; fi; exec node_modules/.bin/next start -H 0.0.0.0 -p 3000"]
