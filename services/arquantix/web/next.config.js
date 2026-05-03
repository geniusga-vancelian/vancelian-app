const path = require('path')
const fs = require('fs')

/**
 * Monorepo : `next dev` s’exécute dans `services/arquantix/web` — Next ne charge pas le `.env` à la racine du dépôt.
 * On charge ../../.env si présent pour que R2 / DATABASE_URL partagés avec Docker soient visibles en local.
 * En conteneur, ce fichier n’existe généralement pas ; l’env est injecté par Compose.
 */
;(function loadRepoRootEnv() {
  const rootEnv = path.join(__dirname, '..', '..', '.env')
  if (!fs.existsSync(rootEnv)) return
  try {
    require('dotenv').config({ path: rootEnv })
  } catch {
    /* module dotenv absent (ex. image minimale) ou erreur de lecture */
  }
})()

/** @type {import('next').NextConfig} */
const nextConfig = {
  /**
   * Force la transpilation de ces dépendances (petites libs ESM/CJS) pour éviter
   * des chunks RSC où `__webpack_require__(id)` tombe sur `undefined` en dev.
   */
  transpilePackages: ['clsx', 'tailwind-merge'],
  eslint: {
    // Violations ESLint héritées : ne pas bloquer `next build` (lint séparé si besoin).
    ignoreDuringBuilds: true,
  },
  // output: 'standalone', // Désactivé pour utiliser next start
  experimental: {
    instrumentationHook: true,
    /**
     * Externalise les packages serveur qui :
     * - utilisent du `require` dynamique non bundlable (`mjml`, `mjml-core` chargent les composants par nom),
     * - embarquent un binaire WASM (`htmlnano` → Biome wasm), introuvable dans `.next/server/vendor-chunks/`
     *   après bundle webpack (cf. erreur `ENOENT: …biome_wasm_bg.wasm`).
     *
     * Ces packages sont alors `require()`-és depuis `node_modules/` au runtime, intacts.
     */
    serverComponentsExternalPackages: [
      'mjml',
      'mjml-core',
      'mjml-validator',
      'htmlnano',
    ],
  },
  // Timeouts de watch : utiles sur stockage cloud lent (OneDrive, iCloud) ou gros monorepos
  webpack: (config, { dev }) => {
    // Augmenter les timeouts pour les opérations de fichiers
    config.watchOptions = {
      ...config.watchOptions,
      poll: 1000,
      aggregateTimeout: 300,
      ignored: ['**/node_modules', '**/.git', '**/.next'],
    }
    // Cache fichier webpack souvent corrompu sur FS synchronisé (iCloud / OneDrive)
    // → ENOENT rename *.pack.gz + modules `undefined` dans __webpack_require__.
    // NEXT_WEBPACK_DISABLE_CACHE=1 : pas de cache du tout (plus lent, plus stable).
    if (process.env.NEXT_WEBPACK_DISABLE_CACHE === '1') {
      config.cache = false
    } else if (
      dev &&
      process.env.NEXT_WEBPACK_MEMORY_CACHE === '1' &&
      config.cache &&
      typeof config.cache === 'object'
    ) {
      config.cache = { type: 'memory', maxGenerations: 1 }
    }
    return config
  },
}

module.exports = nextConfig
