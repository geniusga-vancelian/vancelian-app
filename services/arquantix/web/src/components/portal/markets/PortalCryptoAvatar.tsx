'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  cryptoBrandColor,
  normalizeCryptoBaseTicker,
  resolveCryptoAvatarSources,
} from '@/lib/portal/cryptoInstrumentAssets'
import { cn } from '@/lib/utils'

type Props = {
  ticker: string
  symbol?: string
  apiLogoUrl?: string | null
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const SIZE_PX = { sm: 24, md: 36, lg: 40 } as const

/**
 * Avatar crypto — même priorité que Flutter `CryptoAvatar` :
 * SVG packagé (`/crypto_svgs/*.svg`) → logo API → PNG `/media/crypto_logos/`.
 */
export function PortalCryptoAvatar({
  ticker,
  symbol,
  apiLogoUrl,
  size = 'lg',
  className,
}: Props) {
  const px = SIZE_PX[size]
  const sources = useMemo(
    () => resolveCryptoAvatarSources(ticker, apiLogoUrl),
    [ticker, apiLogoUrl],
  )
  const [sourceIndex, setSourceIndex] = useState(0)

  useEffect(() => {
    setSourceIndex(0)
  }, [ticker, apiLogoUrl])

  const baseTicker = normalizeCryptoBaseTicker(symbol ?? ticker)
  const bg = cryptoBrandColor(baseTicker)
  const currentSrc = sources[sourceIndex]

  if (!currentSrc) {
    return (
      <span
        className={cn(
          'inline-flex shrink-0 items-center justify-center rounded-full font-ui font-semibold text-white',
          className,
        )}
        style={{ width: px, height: px, backgroundColor: bg, fontSize: size === 'sm' ? 10 : 12 }}
        aria-hidden
      >
        {baseTicker.slice(0, 3)}
      </span>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={currentSrc}
      alt=""
      width={px}
      height={px}
      className={cn('shrink-0 rounded-full object-cover', className)}
      style={{ width: px, height: px, backgroundColor: bg }}
      loading="lazy"
      decoding="async"
      onError={() => {
        setSourceIndex((index) => index + 1)
      }}
    />
  )
}
