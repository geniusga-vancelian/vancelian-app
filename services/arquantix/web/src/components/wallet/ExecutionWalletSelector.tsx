'use client'

import { useExecutionWallet } from '@/lib/wallet/useExecutionWallet'
import { isLocalMockVerifiedExternalWallet } from '@/lib/wallet/externalWalletMock'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import { getExternalWalletBaseChainId } from '@/lib/wallet/externalWalletConstants'
import { formatEvmNetworkShort } from '@/lib/portal/evmNetworkLabel'
import { cn } from '@/lib/utils'

function formatAddress(address: string): string {
  const trimmed = address.trim()
  if (trimmed.length <= 12) return trimmed
  return `${trimmed.slice(0, 6)}…${trimmed.slice(-4)}`
}

type Props = {
  className?: string
  showGasHint?: boolean
  /** swap : libellé réseau LI.FI ; morpho : Base ; défaut : Morpho */
  context?: 'swap' | 'morpho' | 'default'
  fromChain?: string
}

function externalWalletNetworkHint(context: Props['context'], fromChain?: string): string {
  if (context === 'swap' && fromChain) {
    return ` · réseau ${SWAP_CHAIN_LABELS[fromChain] ?? fromChain}`
  }
  if (context === 'morpho' || context === 'default') {
    return ` · réseau ${formatEvmNetworkShort(getExternalWalletBaseChainId())} pour Morpho`
  }
  return ''
}

export function ExecutionWalletSelector({
  className,
  showGasHint = true,
  context = 'default',
  fromChain,
}: Props) {
  const {
    mode,
    setMode,
    externalWallets,
    selectedExternalWalletId,
    setSelectedExternalWalletId,
    privyEmbeddedAddress,
    loading,
    mockWalletAvailable,
  } = useExecutionWallet()

  const selectedExternal = externalWallets.find((row) => row.id === selectedExternalWalletId) ?? externalWallets[0]
  const selectedIsMock = selectedExternal ? isLocalMockVerifiedExternalWallet(selectedExternal) : false

  return (
    <div className={cn('rounded-v-card border border-v-border bg-v-card px-4 py-3 font-ui text-[13px]', className)}>
      <p className="m-0 font-medium text-v-fg">Méthode de transaction</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={loading}
          onClick={() => setMode('privy_embedded')}
          className={cn(
            'rounded-v-control border px-3 py-2 text-left transition-colors',
            mode === 'privy_embedded'
              ? 'border-v-fg bg-v-fg text-white'
              : 'border-v-border bg-white text-v-fg-muted hover:text-v-fg',
          )}
        >
          <span className="block font-medium">Wallet Vancelian</span>
          <span className="mt-0.5 block text-[12px] opacity-80">Embedded Privy</span>
        </button>
        <button
          type="button"
          disabled={loading || externalWallets.length === 0}
          onClick={() => setMode('external_evm')}
          className={cn(
            'rounded-v-control border px-3 py-2 text-left transition-colors',
            mode === 'external_evm'
              ? 'border-v-fg bg-v-fg text-white'
              : 'border-v-border bg-white text-v-fg-muted hover:text-v-fg',
            externalWallets.length === 0 && 'cursor-not-allowed opacity-60',
          )}
        >
          <span className="block font-medium">{selectedIsMock ? 'Local Mock Wallet' : 'MetaMask / externe'}</span>
          <span className="mt-0.5 block text-[12px] opacity-80">
            {selectedIsMock ? 'Sandbox dev sans extension' : 'Gas payé par vous'}
          </span>
        </button>
      </div>

      {mode === 'privy_embedded' ? (
        <p className="m-0 mt-3 text-v-fg-muted">
          {privyEmbeddedAddress
            ? `Adresse : ${formatAddress(privyEmbeddedAddress)} · gas sponsorisé (si activé Privy)`
            : 'Créez votre wallet Vancelian depuis Mon wallet.'}
        </p>
      ) : selectedExternal ? (
        <div className="mt-3 space-y-2">
          {externalWallets.length > 1 ? (
            <label className="flex flex-col gap-1 text-v-fg-muted">
              Wallet externe
              <select
                value={selectedExternal.id}
                onChange={(e) => setSelectedExternalWalletId(e.target.value)}
                className="h-10 rounded-v-control border border-v-border bg-white px-3 text-v-fg"
              >
                {externalWallets.map((wallet) => (
                  <option key={wallet.id} value={wallet.id}>
                    {formatAddress(wallet.address)} ({wallet.walletProvider})
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p className="m-0 text-v-fg-muted">
              Adresse : {formatAddress(selectedExternal.address)}
              {selectedIsMock
                ? ' · wallet mock sandbox'
                : externalWalletNetworkHint(context, fromChain)}
            </p>
          )}
          {showGasHint ? (
            <p className="m-0 text-amber-800">
              {selectedIsMock
                ? 'Transactions simulées localement — pas de MetaMask ni gas réel.'
                : 'Les frais réseau seront payés directement depuis ce wallet.'}
            </p>
          ) : null}
        </div>
      ) : (
        <p className="m-0 mt-3 text-v-fg-muted">
          Aucun wallet externe vérifié. Liez MetaMask depuis Mon wallet
          {mockWalletAvailable ? ' ou utilisez le Local Mock Wallet.' : '.'}
        </p>
      )}
    </div>
  )
}
