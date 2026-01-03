#!/bin/sh
set -e

echo "🚀 Strapi Docker Entrypoint"

# Wait for database to be ready
echo "⏳ Waiting for PostgreSQL..."
until nc -z arquantix-db 5432; do
  sleep 1
done
echo "✅ PostgreSQL is ready"

# Install dependencies if needed
if [ ! -d node_modules ] || [ ! -f node_modules/.bin/strapi ]; then
  echo "📦 Installing dependencies..."
  npm install
fi

# Build admin panel if not built
if [ ! -d node_modules/@strapi/admin/dist ]; then
  echo "🔨 Building Strapi admin panel (this may take 2-3 minutes)..."
  npm run build || {
    echo "⚠️ Build failed, trying develop mode anyway..."
  }
fi

# Start Strapi in develop mode
echo "🚀 Starting Strapi in develop mode..."
exec npm run develop

