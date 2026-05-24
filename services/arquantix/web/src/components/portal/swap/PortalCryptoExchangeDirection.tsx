'use client'

import { ArrowRight } from 'lucide-react'

import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'

type Props = {
  fromAsset: string
  toAsset: string
  fromLabel?: string
  toLabel?: string
  className?: string
}

export function PortalCryptoExchangeDirection({
  fromAsset,
  toAsset,
  fromLabel,
  toLabel,
  className,
}: Props) {
  return (
    <div className={`flex items-center justify-center gap-3 ${className ?? ''}`}>
      <AssetBubble asset={fromAsset} label={fromLabel ?? fromAsset} />
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-v-card text-v-fg-muted shadow-v-subtle">
        <ArrowRight className="h-4 w-4" />
      </span>
      <AssetBubble asset={toAsset} label={toLabel ?? toAsset} />
    </div>
  )
}

function AssetBubble({ asset, label }: { asset: string; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <PortalCryptoAvatar
        ticker={asset}
        symbol={tickerToProviderSymbol(asset)}
        size="lg"
      />
      <span className="font-ui text-[12px] font-semibold text-v-fg">{label}</span>
    </div>
  )
}
