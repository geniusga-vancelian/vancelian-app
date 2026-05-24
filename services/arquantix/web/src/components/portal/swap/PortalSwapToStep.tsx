'use client'

import { useMemo, useState } from 'react'

import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalSwapFlowShell } from '@/components/portal/swap/PortalSwapFlowShell'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import { defaultChainForAsset } from '@/lib/portal/swapFlowFormat'
import type { SwapCatalogAsset } from '@/lib/portal/swapFlowTypes'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import { cn } from '@/lib/utils'

type Props = {
  assets: SwapCatalogAsset[]
  onSelect: (asset: string, chain: string) => void
  onBack?: () => void
}

export function PortalSwapToStep({ assets, onSelect, onBack }: Props) {
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return assets
    return assets.filter(
      (a) =>
        a.symbol.toLowerCase().includes(q) ||
        a.display_name.toLowerCase().includes(q),
    )
  }, [assets, query])

  return (
    <PortalSwapFlowShell title="Swap" onBack={onBack}>
      <div className="flex flex-col gap-5">
        <div>
          <p className="m-0 font-ui text-[13px] uppercase tracking-wide text-v-fg-muted">Étape 1</p>
          <h2 className="mt-2 mb-0 font-ui text-[24px] font-bold leading-tight text-v-fg">
            Vers quelle crypto ?
          </h2>
          <p className="mt-2 mb-0 font-ui text-[15px] text-v-fg-muted">
            USDC, USDT ou ETH — pilote Ethereum mainnet (same-chain).
          </p>
        </div>

        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher"
          className="w-full rounded-full border border-v-border bg-white px-4 py-3 font-ui text-[15px] shadow-v-subtle outline-none focus:border-v-accent"
        />

        <article className="overflow-hidden rounded-v-card border border-v-border bg-v-card shadow-v-subtle">
          <ul className="m-0 list-none p-0">
            {filtered.map((asset) => (
              <AssetRow key={asset.symbol} asset={asset} onSelect={onSelect} />
            ))}
          </ul>
        </article>
      </div>
    </PortalSwapFlowShell>
  )
}

function AssetRow({
  asset,
  onSelect,
}: {
  asset: SwapCatalogAsset
  onSelect: (asset: string, chain: string) => void
}) {
  const [chain, setChain] = useState(defaultChainForAsset(asset.symbol, asset.chains))

  return (
    <li className="border-b border-v-border last:border-b-0">
      <button
        type="button"
        className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-v-card-hover"
        onClick={() => onSelect(asset.symbol, chain)}
      >
        <PortalCryptoAvatar
          ticker={asset.symbol}
          symbol={tickerToProviderSymbol(asset.symbol)}
          size="md"
        />
        <span className="min-w-0 flex-1">
          <span className="block font-ui text-[15px] font-semibold text-v-fg">{asset.display_name}</span>
          <span className="mt-0.5 block font-ui text-[13px] text-v-fg-muted">{asset.symbol}</span>
        </span>
      </button>
      {asset.chains.length > 1 ? (
        <div className="flex flex-wrap gap-2 px-4 pb-3">
          {asset.chains.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setChain(c)}
              className={cn(
                'rounded-full border px-3 py-1 font-ui text-[12px] font-medium transition-colors',
                chain === c
                  ? 'border-v-accent bg-v-accent/10 text-v-accent'
                  : 'border-v-border bg-white text-v-fg-muted hover:border-v-fg-muted',
              )}
            >
              {SWAP_CHAIN_LABELS[c] ?? c}
            </button>
          ))}
        </div>
      ) : null}
    </li>
  )
}
