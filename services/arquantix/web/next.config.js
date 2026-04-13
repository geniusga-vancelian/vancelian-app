/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // Violations ESLint héritées : ne pas bloquer `next build` (lint séparé si besoin).
    ignoreDuringBuilds: true,
  },
  // output: 'standalone', // Désactivé pour utiliser next start
  experimental: {
    instrumentationHook: true,
  },
  // Configuration pour éviter les problèmes de timeout avec OneDrive
  webpack: (config, { isServer }) => {
    // Augmenter les timeouts pour les opérations de fichiers
    config.watchOptions = {
      ...config.watchOptions,
      poll: 1000,
      aggregateTimeout: 300,
      ignored: ['**/node_modules', '**/.git', '**/.next'],
    }
    // Ne pas désactiver le cache webpack par défaut : risque de chunks
    // manquants (ex. `vendor-chunks/tslib.js`). Avec OneDrive : NEXT_WEBPACK_DISABLE_CACHE=1
    if (process.env.NEXT_WEBPACK_DISABLE_CACHE === '1') {
      config.cache = false
    }
    return config
  },
}

module.exports = nextConfig
