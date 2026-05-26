'use client'

import { useMemo } from 'react'

import { resolveCryptoAvatarSources } from '@/lib/portal/cryptoInstrumentAssets'
import { cn } from '@/lib/utils'

type Props = {
  fromAsset: string
  toAsset: string
  className?: string
}

function CryptoAvatarBubble({ asset }: { asset: string }) {
  const sources = useMemo(() => resolveCryptoAvatarSources(asset), [asset])
  const src = sources[0]

  if (!src) {
    return (
      <span className="flex h-full w-full items-center justify-center bg-v-fg-05 font-ui text-[10px] font-semibold text-v-fg">
        {asset.slice(0, 3)}
      </span>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="" className="h-full w-full object-cover" />
  )
}

/** Avatar échange crypto (from + to) — preview/17 ligne swap + preview/41. */
export function AppTxExchangeAvatar({ fromAsset, toAsset, className }: Props) {
  const from = fromAsset.trim().toUpperCase()
  const to = toAsset.trim().toUpperCase()

  return (
    <span className={cn('avt-x avt-x--52 shrink-0', className)}>
      <span className="avt-x__source">
        <CryptoAvatarBubble asset={from} />
      </span>
      <span className="avt-x__result">
        <CryptoAvatarBubble asset={to} />
      </span>
    </span>
  )
}
