import { getDefaultConfig } from '@rainbow-me/rainbowkit'
import { cookieStorage, createStorage, http, type Config } from 'wagmi'
import { arbitrum, base, mainnet, optimism, polygon } from 'wagmi/chains'

import { MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'

/** Chaînes autorisées pour wallet externe (Morpho Base + LI.FI). */
export const EXTERNAL_WALLET_CHAINS = [base, mainnet, polygon, arbitrum, optimism] as const

export const EXTERNAL_WALLET_CHAIN_IDS = EXTERNAL_WALLET_CHAINS.map((chain) => chain.id)

export function isAllowedExternalWalletChainId(chainId: number): boolean {
  return (EXTERNAL_WALLET_CHAIN_IDS as readonly number[]).includes(chainId)
}

function readPublicEnv(value: string | undefined): string | undefined {
  const trimmed = value?.trim()
  return trimmed || undefined
}

/** Accès statique requis : Next.js n’inline pas process.env[name] dans le bundle client. */
export function getWalletConnectProjectId(): string {
  return (
    readPublicEnv(process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID) ??
    '00000000000000000000000000000000'
  )
}

export function isWalletConnectConfigured(): boolean {
  const id = readPublicEnv(process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID)
  return Boolean(id && id !== '00000000000000000000000000000000')
}

function resolvePortalAppUrl(): string {
  return readPublicEnv(process.env.NEXT_PUBLIC_PORTAL_APP_URL) ?? 'https://app.vancelian.finance'
}

function resolveBaseRpcUrl(): string {
  return (
    readPublicEnv(process.env.NEXT_PUBLIC_BASE_RPC_URL) ??
    readPublicEnv(process.env.NEXT_PUBLIC_BASE_RPC_URL_FALLBACK) ??
    'https://mainnet.base.org'
  )
}

function resolveMainnetRpcUrl(): string {
  return readPublicEnv(process.env.NEXT_PUBLIC_ETHEREUM_RPC_URL) ?? 'https://ethereum.publicnode.com'
}

function buildExternalWalletWagmiConfig(): Config {
  const baseRpc = resolveBaseRpcUrl()
  const mainnetRpc = resolveMainnetRpcUrl()
  const portalAppUrl = resolvePortalAppUrl()

  return getDefaultConfig({
    appName: 'Vancelian',
    appDescription: 'Portail Vancelian — wallets externes MetaMask / WalletConnect',
    appUrl: portalAppUrl,
    projectId: getWalletConnectProjectId(),
    chains: [...EXTERNAL_WALLET_CHAINS],
    ssr: true,
    storage: createStorage({
      storage: cookieStorage,
    }),
    walletConnectParameters: {
      metadata: {
        name: 'Vancelian',
        description: 'Portail Vancelian',
        url: portalAppUrl,
        icons: [`${portalAppUrl}/favicon.ico`],
      },
    },
    transports: {
      [base.id]: http(baseRpc),
      [mainnet.id]: http(mainnetRpc),
      [polygon.id]: http('https://polygon-rpc.com'),
      [arbitrum.id]: http('https://arb1.arbitrum.io/rpc'),
      [optimism.id]: http('https://mainnet.optimism.io'),
    },
  })
}

/** Singleton wagmi — lazy init pour éviter getDefaultConfig() au collect page data des routes API. */
let externalWalletWagmiConfigSingleton: Config | undefined

export function getExternalWalletWagmiConfig(): Config {
  if (!externalWalletWagmiConfigSingleton) {
    externalWalletWagmiConfigSingleton = buildExternalWalletWagmiConfig()
  }
  return externalWalletWagmiConfigSingleton
}

export function getExternalWalletBaseChainId(): number {
  return MORPHO_CHAIN_ID
}
