import type { PortalChain } from '@/config/portalChains'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'

export function buildPortalScopeQueryParams(
  chain: PortalChain,
  walletScope: PortalWalletScope | null,
): URLSearchParams {
  const params = new URLSearchParams()
  params.set('portal_chain', chain)
  if (walletScope?.address?.trim()) {
    params.set('wallet_address', walletScope.address.trim())
  }
  return params
}

export function appendPortalScopeQuery(
  url: string,
  chain: PortalChain,
  walletScope: PortalWalletScope | null,
): string {
  const params = buildPortalScopeQueryParams(chain, walletScope)
  const query = params.toString()
  if (!query) return url
  return url.includes('?') ? `${url}&${query}` : `${url}?${query}`
}

export function buildPortalScopeCacheSuffix(
  chain: PortalChain,
  walletScopeId: string | null,
): string {
  return `${chain}:${walletScopeId ?? 'none'}`
}
