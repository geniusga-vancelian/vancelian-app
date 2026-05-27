const path = require('path')
const fs = require('fs')

const privyAuthCjs = path.join(__dirname, 'node_modules/@privy-io/react-auth/dist/cjs')
const metamaskAsyncStorageStub = path.join(__dirname, 'src/lib/wallet/metamaskAsyncStorageStub.js')

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

function isTruthyEnvFlag(raw) {
  const v = (raw || '').trim().toLowerCase()
  return v === '1' || v === 'true' || v === 'yes'
}

/** Active le mock Privy OTP si TWO_FACTOR_DEV_* est déjà configuré (stack locale). */
function applyPrivyOtpDevMockDefaults() {
  const explicitOff = ['0', 'false', 'no'].includes(
    (process.env.PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED || '').trim().toLowerCase(),
  )
  if (explicitOff) return

  if (process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED?.trim()) return
  if (process.env.PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED?.trim()) return

  const devCode = (process.env.TWO_FACTOR_DEV_FIXED_CODE || '').trim()
  if (!isTruthyEnvFlag(process.env.TWO_FACTOR_DEV_EXPOSE_CODE) || !/^\d{6}$/.test(devCode)) {
    return
  }

  process.env.PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED = 'true'
  process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED = 'true'
}

/**
 * Monorepo : `next dev` s’exécute dans `services/arquantix/web` — Next ne charge pas les `.env` racine par défaut.
 * Ordre : racine (.env, .env.arquantix) → web/.env → web/.env.local (surcharge locale).
 * Build Docker : passer les NEXT_PUBLIC_* en ARG (le repo root n’est pas dans l’image builder).
 */
;(function loadMonorepoEnv() {
  try {
    require('dotenv')
  } catch {
    return
  }

  const dotenv = require('dotenv')
  const webDir = __dirname

  for (const fileName of ['.env', '.env.arquantix']) {
    const envPath = path.join(repoRoot, fileName)
    if (!fs.existsSync(envPath)) continue
    try {
      dotenv.config({ path: envPath })
    } catch {
      /* erreur de lecture */
    }
  }

  for (const fileName of ['.env']) {
    const envPath = path.join(webDir, fileName)
    if (!fs.existsSync(envPath)) continue
    try {
      dotenv.config({ path: envPath })
    } catch {
      /* erreur de lecture */
    }
  }

  const localPath = path.join(webDir, '.env.local')
  if (fs.existsSync(localPath)) {
    try {
      dotenv.config({ path: localPath, override: true })
    } catch {
      /* erreur de lecture */
    }
  }

  bridgeEnv('NEXT_PUBLIC_PRIVY_APP_ID', 'PRIVY_APP_ID', 'NEXT_PUBLIC_PRIVY_APP_ID')
  bridgeEnv('PRIVY_APP_ID', 'NEXT_PUBLIC_PRIVY_APP_ID')
  bridgeEnv('NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID', 'PRIVY_WEB_CLIENT_ID', 'NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID')
  bridgeEnv(
    'NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED',
    'PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED',
    'NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED',
  )
  bridgeEnv(
    'NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE',
    'PORTAL_PRIVY_OTP_DEV_FIXED_CODE',
    'TWO_FACTOR_DEV_FIXED_CODE',
    'NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE',
  )

  applyPrivyOtpDevMockDefaults()
})()

/** @type {import('next').NextConfig} */
const nextConfig = {
  /**
   * Force la transpilation de ces dépendances (petites libs ESM/CJS) pour éviter
   * des chunks RSC où `__webpack_require__(id)` tombe sur `undefined` en dev.
   */
  transpilePackages: [
    'clsx',
    'tailwind-merge',
    '@privy-io/react-auth',
    '@rainbow-me/rainbowkit',
    '@wagmi/connectors',
    '@metamask/sdk',
  ],
  eslint: {
    // Violations ESLint héritées : ne pas bloquer `next build` (lint séparé si besoin).
    ignoreDuringBuilds: true,
  },
  // output: 'standalone', // Désactivé pour utiliser next start
  experimental: {
    instrumentationHook: true,
    turbo: {
      // Turbopack n’accepte pas les chemins absolus dans resolveAlias (Next 14.2).
      resolveAlias: {
        '@react-native-async-storage/async-storage': './src/lib/wallet/metamaskAsyncStorageStub.js',
        '@privy-io/react-auth': './node_modules/@privy-io/react-auth/dist/cjs/index.js',
        '@privy-auth-internal/provider':
          './node_modules/@privy-io/react-auth/dist/cjs/privy-provider-zm0SWrLy.js',
        '@privy-auth-internal/context':
          './node_modules/@privy-io/react-auth/dist/cjs/internal-context-B_aIJuQh.js',
      },
    },
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
    config.resolve.alias = {
      ...(config.resolve.alias ?? {}),
      // MetaMask SDK (via @wagmi/connectors) — dépendance React Native optionnelle.
      '@react-native-async-storage/async-storage': metamaskAsyncStorageStub,
    }

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
    // Polling uniquement sur FS lents (iCloud/OneDrive) — coûteux sur disque local.
    config.watchOptions = {
      ...config.watchOptions,
      aggregateTimeout: 300,
      ignored: ['**/node_modules', '**/.git', '**/.next'],
      ...(process.env.NEXT_WEBPACK_POLL === '1' ? { poll: 1000 } : {}),
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
    // WalletConnect / RainbowKit — dépendances optionnelles non bundlables côté serveur SSR uniquement.
    if (isServer) {
      const walletConnectExternals = ['pino-pretty', 'lokijs', 'encoding']
      if (typeof config.externals === 'function') {
        const originalExternals = config.externals
        config.externals = async (ctx) => {
          const resolved = await originalExternals(ctx)
          if (Array.isArray(resolved)) return [...resolved, ...walletConnectExternals]
          return resolved
        }
      } else {
        config.externals = [...(config.externals ?? []), ...walletConnectExternals]
      }
    }
    return config
  },
}

module.exports = nextConfig
