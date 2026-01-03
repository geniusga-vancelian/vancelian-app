# --- deps ---
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# --- build ---
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Ensure public directory exists for Next.js build
RUN mkdir -p ./public
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

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV HOST="0.0.0.0"
ENV PATH="/app/node_modules/.bin:$PATH"

# Next.js start with explicit hostname
CMD ["node_modules/.bin/next", "start", "-H", "0.0.0.0", "-p", "3000"]
