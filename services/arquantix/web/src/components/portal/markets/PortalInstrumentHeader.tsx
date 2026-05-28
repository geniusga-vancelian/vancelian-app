'use client'

import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { formatInstrumentChange24h } from '@/lib/portal/instrumentDetailFormat'
import { cn } from '@/lib/utils'

type Props = {
  ticker: string
  symbol: string
  name: string
  logoUrl: string | null
  priceLabel: string
  change24hPct: number
  isFavorite: boolean
  favoriteBusy: boolean
  onToggleFavorite: () => void
}

/** En-tête fiche actif — handoff `.ast-header`. */
export function PortalInstrumentHeader({
  ticker,
  symbol,
  name,
  logoUrl,
  priceLabel,
  change24hPct,
  isFavorite,
  favoriteBusy,
  onToggleFavorite,
}: Props) {
  const up = change24hPct >= 0

  return (
    <header className="ast-header">
      <div className="ast-header__row">
        <span className="ast-header__ic" aria-hidden>
          <PortalCryptoAvatar ticker={ticker} symbol={symbol} apiLogoUrl={logoUrl} size="lg" />
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h1 className="ast-header__name">{name}</h1>
          <span className="ast-header__sym">
            {ticker} · Crypto tokenisée
          </span>
        </div>
        <button
          type="button"
          onClick={onToggleFavorite}
          disabled={favoriteBusy}
          aria-pressed={isFavorite}
          aria-label={isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
          className={cn('ast-fav', isFavorite && 'is-on')}
        >
          <KalaiIcon name="star" size={20} />
          <span className="ast-fav__lbl">{isFavorite ? 'Favori' : 'Ajouter aux favoris'}</span>
        </button>
      </div>

      <div className="ast-price-row">
        <span className="ast-price">{priceLabel}</span>
        <span className={cn('ast-chg', up ? 'ast-chg--up' : 'ast-chg--down')}>
          {formatInstrumentChange24h(change24hPct)}
          <span className="ast-chg__lbl">aujourd&apos;hui</span>
        </span>
      </div>
    </header>
  )
}
