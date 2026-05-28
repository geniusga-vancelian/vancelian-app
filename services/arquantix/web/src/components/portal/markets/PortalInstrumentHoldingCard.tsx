'use client'

import { useEffect, useMemo, useState } from 'react'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { PortalCryptoWalletDetailPayload } from '@/lib/portal/cryptoWalletTypes'
import { formatCryptoMoney, selectMoneyValue } from '@/lib/portal/cryptoWalletFormat'
import { formatCryptoPrice } from '@/lib/portal/instrumentDetailFormat'
import { portalSwapBuyRoute, portalSwapSellRoute } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  ticker: string
  priceUsd: number
  buyHref?: string
  sellHref?: string
}

/** Carte position détenue — handoff `.ast-pos`. */
export function PortalInstrumentHoldingCard({ ticker, priceUsd, buyHref, sellHref }: Props) {
  const [walletData, setWalletData] = useState<PortalCryptoWalletDetailPayload | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const res = await fetch(`/api/portal/crypto-wallet/${encodeURIComponent(ticker)}`, {
          credentials: 'include',
          cache: 'no-store',
        })
        if (!res.ok) return
        const json = (await res.json()) as PortalCryptoWalletDetailPayload
        if (!cancelled) setWalletData(json)
      } catch {
        // Position absente ou indisponible — état vide conservé.
      }
    })()
    return () => {
      cancelled = true
    }
  }, [ticker])

  const holding = useMemo(() => {
    const detail = walletData?.detail
    if (!detail) return null
    const qty = Number.parseFloat(String(detail.volume).replace(',', '.')) || 0
    if (qty <= 0) return null

    const currency = walletData?.currency ?? 'EUR'
    const totalValue =
      selectMoneyValue(currency, detail.totalValueEur, detail.totalValueUsd) ?? qty * priceUsd
    const costBasis =
      selectMoneyValue(currency, detail.avgBuyPriceEur, detail.avgBuyPriceUsd) ??
      detail.averagePurchasePrice ??
      detail.costBasis ??
      0
    const pl =
      selectMoneyValue(currency, detail.unrealizedGainEur, detail.unrealizedGainUsd) ??
      detail.unrealizedGains ??
      totalValue - costBasis * qty
    const plPct =
      detail.unrealizedGainsPct ??
      (costBasis > 0 ? ((priceUsd - costBasis) / costBasis) * 100 : 0)

    return {
      qty,
      totalValue,
      costBasis,
      pl,
      plPct,
      currency,
      volumeLabel: detail.volume,
    }
  }, [priceUsd, walletData])

  const resolvedBuyHref = buyHref ?? portalSwapBuyRoute(ticker)
  const resolvedSellHref = sellHref ?? portalSwapSellRoute(ticker)

  if (!holding) {
    return (
      <div className="ast-pos ast-pos--empty">
        <div className="ast-pos__eyebrow">Votre position</div>
        <p className="ast-pos__empty">Aucune position sur {ticker} pour le moment.</p>
        <div className="ast-pos__cta">
          <PortalNavLink href={resolvedBuyHref} className="btn btn--primary no-underline">
            <KalaiIcon name="arrow-down" size={16} />
            Acheter
          </PortalNavLink>
        </div>
      </div>
    )
  }

  const up = holding.pl >= 0

  return (
    <div className="ast-pos">
      <div className="ast-pos__eyebrow">Votre position</div>

      <div className="ast-pos__main">
        <span className="ast-pos__value v-tnum">
          {formatCryptoMoney(holding.totalValue, holding.currency)}
        </span>
        <span className="ast-pos__qty v-tnum">
          {holding.volumeLabel} {ticker}
        </span>
      </div>

      <div className={cn('ast-pos__pl', up ? 'ast-pos__pl--up' : 'ast-pos__pl--down')}>
        <span className="v-tnum">
          {up ? '+ ' : '− '}
          {formatCryptoMoney(Math.abs(holding.pl), holding.currency)}
        </span>
        <span className="ast-pos__pl-pct v-tnum">
          ({up ? '+ ' : '− '}
          {Math.abs(holding.plPct).toFixed(2).replace('.', ',')} %)
        </span>
      </div>

      <div className="ast-pos__grid">
        <div className="ast-pos__cell">
          <span className="ast-pos__k">Prix de revient</span>
          <span className="ast-pos__v v-tnum">{formatCryptoPrice(holding.costBasis, 'USD')}</span>
        </div>
        <div className="ast-pos__cell">
          <span className="ast-pos__k">Cours actuel</span>
          <span className="ast-pos__v v-tnum">{formatCryptoPrice(priceUsd, 'USD')}</span>
        </div>
      </div>

      <div className="ast-pos__cta">
        <PortalNavLink href={resolvedBuyHref} className="btn btn--primary no-underline">
          <KalaiIcon name="arrow-down" size={16} />
          Acheter
        </PortalNavLink>
        <PortalNavLink href={resolvedSellHref} className="btn btn--secondary no-underline">
          <KalaiIcon name="arrow-up" size={16} />
          Vendre
        </PortalNavLink>
      </div>
    </div>
  )
}
