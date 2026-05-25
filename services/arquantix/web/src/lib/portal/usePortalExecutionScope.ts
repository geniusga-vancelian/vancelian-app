'use client'

import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import {
  isPortalChainDeFiEnabled,
  isPortalChainSwapEnabled,
  portalChainContextLabel,
  resolvePortalChainSwapKey,
} from '@/lib/portal/portalChainFilter'
import { usePortalWalletScopeContext } from '@/lib/portal/portalWalletScopeContext'
import {
  isPortalScopeExternal,
  portalWalletScopeContextLabel,
} from '@/lib/portal/portalWalletScopeFilter'

export function usePortalExecutionScope() {
  const { chain } = usePortalChainContext()
  const { walletScope, walletScopeId, loading: scopeLoading } = usePortalWalletScopeContext()

  const chainLabel = portalChainContextLabel(chain)
  const walletLabel = portalWalletScopeContextLabel(walletScope)
  const executionAddress = walletScope?.address?.trim() || null
  const swapChainKey = resolvePortalChainSwapKey(chain)
  const swapEnabled = isPortalChainSwapEnabled(chain)
  const deFiEnabled = isPortalChainDeFiEnabled(chain)

  return {
    chain,
    chainLabel,
    walletScope,
    walletScopeId,
    walletLabel,
    executionAddress,
    scopeLoading,
    swapEnabled,
    deFiEnabled,
    swapChainKey,
    isExternalWallet: isPortalScopeExternal(walletScope),
    walletReady: Boolean(executionAddress),
  }
}
