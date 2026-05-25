import { MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'

/** Chaînes autorisées pour wallet externe (Morpho Base + LI.FI). */
export const EXTERNAL_WALLET_CHAIN_IDS = [8453, 1, 137, 42161, 10] as const

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

export function getExternalWalletBaseChainId(): number {
  return MORPHO_CHAIN_ID
}

export function resolvePortalAppUrl(): string {
  return readPublicEnv(process.env.NEXT_PUBLIC_PORTAL_APP_URL) ?? 'https://app.vancelian.finance'
}

export function resolveBaseRpcUrl(): string {
  return (
    readPublicEnv(process.env.NEXT_PUBLIC_BASE_RPC_URL) ??
    readPublicEnv(process.env.NEXT_PUBLIC_BASE_RPC_URL_FALLBACK) ??
    'https://mainnet.base.org'
  )
}

export function resolveMainnetRpcUrl(): string {
  return readPublicEnv(process.env.NEXT_PUBLIC_ETHEREUM_RPC_URL) ?? 'https://ethereum.publicnode.com'
}
