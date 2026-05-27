'use client'

import { useMemo, useState } from 'react'

import { AppAccountSummaryList } from '@/components/design-system/app/AppAccountSummaryList'
import { AppAccountSummaryRow } from '@/components/design-system/app/AppAccountSummaryRow'
import { AppSearchField } from '@/components/design-system/app/AppSearchField'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalPageIntro } from '@/components/portal/PortalPageIntro'
import { PortalSwapFlowShell } from '@/components/portal/swap/PortalSwapFlowShell'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import type { SwapCatalogAsset } from '@/lib/portal/swapFlowTypes'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'

type Props = {
  assets: SwapCatalogAsset[]
  onSelect: (asset: string) => void
  onBack?: () => void
  /** Ex. sell via `?from=` — seule étape de sélection destination. */
  stepEyebrow?: string
  title?: string
  description?: string
}

export function PortalSwapToStep({
  assets,
  onSelect,
  onBack,
  stepEyebrow = 'Step 1',
  title = 'To which crypto?',
  description,
}: Props) {
  const { chainLabel } = usePortalExecutionScope()
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
        <PortalPageIntro
          eyebrow={stepEyebrow}
          title={title}
          description={
            description ??
            `Base assets — same-chain swap on ${chainLabel} via Li.FI (navbar network).`
          }
        />

        <AppSearchField value={query} onChange={setQuery} />

        <AppAccountSummaryList>
          {filtered.map((asset) => (
            <AppAccountSummaryRow
              key={asset.symbol}
              showChevron={false}
              onClick={() => onSelect(asset.symbol)}
              leading={
                <PortalCryptoAvatar
                  ticker={asset.symbol}
                  symbol={tickerToProviderSymbol(asset.symbol)}
                  size="lg"
                  className="!h-[46px] !w-[46px]"
                />
              }
              title={asset.display_name}
              subtitle={asset.symbol}
            />
          ))}
        </AppAccountSummaryList>
      </div>
    </PortalSwapFlowShell>
  )
}
