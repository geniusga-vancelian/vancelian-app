const path = require('path')
const fs = require('fs')

const privyAuthCjs = path.join(__dirname, 'node_modules/@privy-io/react-auth/dist/cjs')

const repoRoot = path.join(__dirname, '..', '..', '..')

function bridgeEnv(target, ...sources) {
  if (process.env[target]?.trim()) return
  for (const source of sources) {
    const value = process.env[source]?.trim()
    if (value) {
      process.env[target] = value
      return
    }
  }
}

/**
 * Monorepo : `next dev` s’exécute dans `services/arquantix/web` — Next ne charge pas les `.env` racine par défaut.
 * On charge `.env` et `.env.arquantix` (source unique Privy / ports / R2) sans écraser `.env.local`.
 * En conteneur Docker, l’env est injecté par Compose.
 */
;(function loadRepoRootEnv() {
  try {
    require('dotenv')
  } catch {
    return
  }

  for (const fileName of ['.env', '.env.arquantix']) {
    const envPath = path.join(repoRoot, fileName)
    if (!fs.existsSync(envPath)) continue
    try {
      require('dotenv').config({ path: envPath })
    } catch {
      /* erreur de lecture */
    }
  }

  bridgeEnv('NEXT_PUBLIC_PRIVY_APP_ID', 'PRIVY_APP_ID', 'NEXT_PUBLIC_PRIVY_APP_ID')
  bridgeEnv('PRIVY_APP_ID', 'NEXT_PUBLIC_PRIVY_APP_ID')
  bridgeEnv('NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID', 'PRIVY_WEB_CLIENT_ID', 'NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID')
})()

/** @type {import('next').NextConfig} */
const nextConfig = {
  /**
   * Force la transpilation de ces dépendances (petites libs ESM/CJS) pour éviter
   * des chunks RSC où `__webpack_require__(id)` tombe sur `undefined` en dev.
   */
  transpilePackages: ['clsx', 'tailwind-merge', '@privy-io/react-auth'],
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
  webpack: (config, { dev, isServer }) => {
    if (!isServer) {
      config.resolve.alias = {
        ...config.resolve.alias,
        // Un seul graphe CJS côté client → contexte captcha / interne partagé avec sendCode().
        '@privy-io/react-auth': path.join(privyAuthCjs, 'index.js'),
        '@privy-auth-internal/provider': path.join(
          privyAuthCjs,
          'privy-provider-zm0SWrLy.js',
        ),
        '@privy-auth-internal/context': path.join(
          privyAuthCjs,
          'internal-context-B_aIJuQh.js',
        ),
      }
    }
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
    // WalletConnect / RainbowKit — dépendances optionnelles non bundlables en App Router SSR.
    config.externals = [...(config.externals ?? []), 'pino-pretty', 'lokijs', 'encoding']
    return config
  },
}

module.exports = nextConfig
