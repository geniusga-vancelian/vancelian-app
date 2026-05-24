'use client'

import { useMemo } from 'react'

import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalSwapFlowShell } from '@/components/portal/swap/PortalSwapFlowShell'
import { formatSwapCryptoAmount, resolveSwapSourceChain } from '@/lib/portal/swapFlowFormat'
import type { SwapCatalogAsset } from '@/lib/portal/swapFlowTypes'
import { SWAP_V1_SAME_CHAIN_ONLY, SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
export type SwapFromOption = {
  asset: string
  name: string
  chain: string
  balance: number
  logoUrl?: string | null
  position?: PortalCryptoPosition
}

type Props = {
  toAsset: string
  toChain: string
  catalog: SwapCatalogAsset[]
  positions: PortalCryptoPosition[]
  onSelect: (option: SwapFromOption) => void
  onBack: () => void
}

export function PortalSwapFromStep({
  toAsset,
  toChain,
  catalog,
  positions,
  onSelect,
  onBack,
}: Props) {
  const options = useMemo(() => buildFromOptions(catalog, positions, toAsset, toChain), [
    catalog,
    positions,
    toAsset,
    toChain,
  ])

  return (
    <PortalSwapFlowShell title="Swap" onBack={onBack}>
      <div className="flex flex-col gap-5">
        <div>
          <p className="m-0 font-ui text-[13px] uppercase tracking-wide text-v-fg-muted">Étape 2</p>
          <h2 className="mt-2 mb-0 font-ui text-[24px] font-bold leading-tight text-v-fg">
            Depuis quel wallet ?
          </h2>
          <p className="mt-2 mb-0 font-ui text-[15px] text-v-fg-muted">
            {SWAP_V1_SAME_CHAIN_ONLY
              ? `Swaps sur ${SWAP_CHAIN_LABELS[toChain] ?? toChain} uniquement — USDC, USDT ou ETH avec solde.`
              : 'Wallets EVM — USDC, USDT ou ETH avec solde.'}
          </p>
        </div>

        {options.length === 0 ? (
          <article className="rounded-v-card border border-v-border bg-v-card p-8 text-center shadow-v-subtle">
            <p className="m-0 font-ui text-[15px] text-v-fg-muted">
              Aucun wallet éligible avec solde. Effectuez un dépôt crypto d&apos;abord.
            </p>
          </article>
        ) : (
          <article className="overflow-hidden rounded-v-card border border-v-border bg-v-card shadow-v-subtle">
            <ul className="m-0 list-none p-0">
              {options.map((opt) => (
                <li key={`${opt.asset}-${opt.chain}`} className="border-b border-v-border last:border-b-0">
                  <button
                    type="button"
                    className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-v-card-hover"
                    onClick={() => onSelect(opt)}
                  >
                    <PortalCryptoAvatar
                      ticker={opt.asset}
                      symbol={tickerToProviderSymbol(opt.asset)}
                      apiLogoUrl={opt.logoUrl}
                      size="md"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block font-ui text-[15px] font-semibold text-v-fg">{opt.name}</span>
                      <span className="mt-0.5 block font-ui text-[13px] text-v-fg-muted">
                        {SWAP_CHAIN_LABELS[opt.chain] ?? opt.chain} · Swap
                      </span>
                    </span>
                    <span className="font-ui text-[15px] font-semibold tabular-nums text-v-fg">
                      {formatSwapCryptoAmount(opt.balance)} {opt.asset}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </article>
        )}
      </div>
    </PortalSwapFlowShell>
  )
}

function buildFromOptions(
  catalog: SwapCatalogAsset[],
  positions: PortalCryptoPosition[],
  toAsset: string,
  toChain: string,
): SwapFromOption[] {
  const catalogBySymbol = new Map(catalog.map((a) => [a.symbol.toUpperCase(), a]))
  const out: SwapFromOption[] = []

  for (const pos of positions) {
    const sym = pos.asset.toUpperCase()
    const meta = catalogBySymbol.get(sym)
    if (!meta) continue
    const balance = pos.availableBalance ?? pos.balance ?? 0
    if (balance <= 0) continue
    const chain = resolveSwapSourceChain(sym, meta.chains, toChain)
    if (SWAP_V1_SAME_CHAIN_ONLY && chain !== toChain) continue
    if (sym === toAsset.toUpperCase() && chain === toChain) continue
    out.push({
      asset: sym,
      name: pos.name || sym,
      chain,
      balance,
      logoUrl: pos.logoUrl,
      position: pos,
    })
  }

  if (out.length === 0) {
    for (const meta of catalog) {
      const chain = resolveSwapSourceChain(meta.symbol, meta.chains, toChain)
      if (SWAP_V1_SAME_CHAIN_ONLY && chain !== toChain) continue
      if (meta.symbol === toAsset && chain === toChain) continue
      out.push({
        asset: meta.symbol,
        name: meta.display_name,
        chain,
        balance: 0,
      })
    }
  }

  return out
}
