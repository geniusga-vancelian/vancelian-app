import { getDefaultConfig } from '@rainbow-me/rainbowkit'
import { cookieStorage, createStorage, http, type Config } from 'wagmi'
import { arbitrum, base, mainnet, optimism, polygon } from 'wagmi/chains'

import {
  getWalletConnectProjectId,
  resolveBaseRpcUrl,
  resolveMainnetRpcUrl,
  resolvePortalAppUrl,
} from '@/lib/wallet/externalWalletConstants'

/** Chaînes wagmi autorisées pour wallet externe (Morpho Base + LI.FI). */
export const EXTERNAL_WALLET_CHAINS = [base, mainnet, polygon, arbitrum, optimism] as const

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
    ssr: false,
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

export {
  EXTERNAL_WALLET_CHAIN_IDS,
  getExternalWalletBaseChainId,
  getWalletConnectProjectId,
  isAllowedExternalWalletChainId,
  isWalletConnectConfigured,
} from '@/lib/wallet/externalWalletConstants'
