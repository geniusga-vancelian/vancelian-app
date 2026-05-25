'use client'

import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { formatEvmNetworkShort } from '@/lib/portal/evmNetworkLabel'
import { getExternalWalletBaseChainId } from '@/lib/wallet/externalWalletConstants'
import { cn } from '@/lib/utils'

function formatAddress(address: string): string {
  const trimmed = address.trim()
  if (trimmed.length <= 12) return trimmed
  return `${trimmed.slice(0, 6)}…${trimmed.slice(-4)}`
}

type Props = {
  className?: string
  /** swap : réseau LI.FI ; defi : Base */
  context?: 'swap' | 'defi'
  showGasHint?: boolean
}

export function PortalExecutionScopeBanner({
  className,
  context = 'defi',
  showGasHint = true,
}: Props) {
  const {
    chainLabel,
    walletLabel,
    executionAddress,
    isExternalWallet,
    scopeLoading,
  } = usePortalExecutionScope()

  const defiNetworkLabel = formatEvmNetworkShort(getExternalWalletBaseChainId())

  return (
    <div
      className={cn(
        'rounded-v-card border border-v-border bg-v-card px-4 py-3 font-ui text-[13px]',
        className,
      )}
    >
      <p className="m-0 font-medium text-v-fg">Réseau et wallet (navbar)</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <div className="rounded-v-control border border-v-border bg-white px-3 py-2">
          <span className="block text-[12px] text-v-fg-muted">Réseau</span>
          <span className="mt-0.5 block font-medium text-v-fg">{chainLabel}</span>
          {context === 'swap' ? (
            <span className="mt-0.5 block text-[12px] text-v-fg-muted">
              Swap sur {chainLabel}
            </span>
          ) : (
            <span className="mt-0.5 block text-[12px] text-v-fg-muted">
              Vaults sur {defiNetworkLabel}
            </span>
          )}
        </div>
        <div className="rounded-v-control border border-v-border bg-white px-3 py-2">
          <span className="block text-[12px] text-v-fg-muted">Wallet</span>
          <span className="mt-0.5 block font-medium text-v-fg">
            {scopeLoading ? '…' : walletLabel}
          </span>
          {executionAddress ? (
            <span className="mt-0.5 block text-[12px] text-v-fg-muted">
              {formatAddress(executionAddress)}
            </span>
          ) : (
            <span className="mt-0.5 block text-[12px] text-v-fg-muted">
              Sélectionnez un wallet dans la navbar
            </span>
          )}
        </div>
      </div>
      {showGasHint && isExternalWallet ? (
        <p className="m-0 mt-3 text-amber-800">
          Les frais réseau seront payés depuis ce wallet externe.
        </p>
      ) : null}
      {showGasHint && !isExternalWallet && executionAddress ? (
        <p className="m-0 mt-3 text-v-fg-muted">
          Wallet Vancelian · gas sponsorisé si activé côté Privy.
        </p>
      ) : null}
    </div>
  )
}
