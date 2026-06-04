'use client'

import { useMemo, useState } from 'react'

import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { LOMBARD_MAX_USER_LTV_PERCENT } from '@/lib/portal/lombard/lombardBorrowLtv'
import { cn } from '@/lib/utils'
import { PortalLombardRiskDial } from '@/components/portal/lombard/PortalLombardRiskDial'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import { formatLombardApyPercent, formatLombardUsdAmount } from '@/lib/portal/lombard/lombardFormat'
import type { LombardBorrowCapacity, LombardMarketSummary, LombardQuoteResult } from '@/lib/portal/lombard/lombardTypes'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'
import {
  estimateLombardGuaranteeDisplay,
  formatBorrowAmountFr,
  lombardBorrowLiquidationDisplay,
  lombardBorrowZoneFor,
  normalizeLombardBorrowAmountForApi,
  parseBorrowAmountInput,
} from '@/lib/portal/lombard/lombardBorrowUi'
import { resolvePortalCollateralBalanceHuman } from '@/lib/portal/lombard/lombardWalletCollateral'

type Props = {
  markets: LombardMarketSummary[]
  positions: PortalCryptoPosition[]
  selectedCollateral: string
  onSelectCollateral: (collateral: string) => void
  capacity: LombardBorrowCapacity | null
  capacityLoading?: boolean
  capacityRefreshing?: boolean
  capacityError?: string | null
  quote: LombardQuoteResult | null
  quoteLoading?: boolean
  quoteRefreshing?: boolean
  quoteError?: string | null
  maxUserLtvPercent?: number
  targetLtvPercent: number
  borrowAmount: string
  onTargetLtvChange: (ltv: number) => void
  onBorrowAmountChange: (amount: string) => void
  onBack: () => void
  onContinue: () => void
  onClose?: () => void
  continueDisabled?: boolean
}

function findGuaranteeBalance(positions: PortalCryptoPosition[], collateral: string): string {
  const row = positions.find((p) => p.asset.toLowerCase() === collateral.toLowerCase())
  if (!row) return '0'
  return String(resolvePortalCollateralBalanceHuman(row))
}

function collateralPriceUsd(positions: PortalCryptoPosition[], collateral: string): number | null {
  const row = positions.find((p) => p.asset.toLowerCase() === collateral.toLowerCase())
  const price = row?.priceUsd ?? row?.priceEur
  return price != null && Number.isFinite(price) ? price : null
}

function formatBalanceFr(value: string): string {
  const n = Number(String(value).replace(',', '.'))
  if (!Number.isFinite(n)) return value
  const digits = n < 1 ? 4 : 2
  return formatBorrowAmountFr(n, digits)
}

export function PortalLombardBorrowForm({
  markets,
  positions,
  selectedCollateral,
  onSelectCollateral,
  capacity,
  capacityLoading = false,
  capacityRefreshing = false,
  capacityError = null,
  quote,
  quoteLoading = false,
  quoteRefreshing = false,
  quoteError = null,
  maxUserLtvPercent,
  targetLtvPercent,
  borrowAmount,
  onTargetLtvChange,
  onBorrowAmountChange,
  onBack,
  onContinue,
  onClose,
  continueDisabled,
}: Props) {
  const [showDetails, setShowDetails] = useState(false)

  const zone = useMemo(() => lombardBorrowZoneFor(targetLtvPercent), [targetLtvPercent])
  const market = useMemo(
    () => markets.find((m) => m.collateral === selectedCollateral) ?? null,
    [markets, selectedCollateral],
  )

  const maxBorrowNum = capacity ? Number(String(capacity.maxBorrowAmount).replace(',', '.')) : 0
  const numericAmount = parseBorrowAmountInput(borrowAmount)
  const apiBorrowAmount = normalizeLombardBorrowAmountForApi(borrowAmount)
  const tooMuch = numericAmount > 0 && maxBorrowNum > 0 && numericAmount > maxBorrowNum
  const guaranteeEstimate = useMemo(
    () =>
      estimateLombardGuaranteeDisplay({
        borrowAmountUsd: numericAmount,
        targetLtvPercent,
        collateral: selectedCollateral,
        collateralPriceUsd: collateralPriceUsd(positions, selectedCollateral),
      }),
    [numericAmount, positions, selectedCollateral, targetLtvPercent],
  )
  const dialMaxLtv = capacity?.maxUserLtvPercent ?? maxUserLtvPercent ?? LOMBARD_MAX_USER_LTV_PERCENT
  const showCapacityGrid = Boolean(capacity) || !capacityLoading

  const canContinue =
    !continueDisabled &&
    !quoteLoading &&
    Boolean(apiBorrowAmount) &&
    numericAmount > 0 &&
    !tooMuch &&
    Boolean(quote) &&
    Boolean(capacity)

  const liquidation = lombardBorrowLiquidationDisplay({
    targetLtvPercent,
    liquidationLltvPercent: capacity?.liquidationLltvPercent ?? market?.liquidationLltvPercent ?? null,
    collateralPriceUsd: collateralPriceUsd(positions, selectedCollateral),
  })

  const lltvPercent = capacity?.liquidationLltvPercent ?? market?.liquidationLltvPercent ?? 77
  const apyLabel = formatLombardApyPercent(
    quote?.borrowApyPercent ?? capacity?.borrowApyPercent ?? market?.borrowApyPercent ?? null,
  )

  return (
    <div className="brw v-card">
      <div className="brw__head">
        <div className="brw__head-text">
          <h3 className="brw__title">Empruntez en gardant vos actifs.</h3>
          <p className="brw__lead">
            Mettez votre crypto en garantie, recevez des USDC sur votre wallet. Aucune durée imposée, vous
            remboursez à votre rythme.
          </p>
        </div>
        {onClose ? (
          <button
            type="button"
            className="inv-head__btn"
            aria-label="Fermer"
            onClick={onClose}
            style={{ width: 32 }}
          >
            <KalaiIcon name="close" size={16} />
          </button>
        ) : null}
      </div>

      <section className="brw-section">
        <h4 className="brw-section__title">
          <span className="brw-section__num">1</span>
          <span>Quelle garantie souhaitez-vous déposer&nbsp;?</span>
        </h4>
        <div className="chain__pills brw-coll">
          {markets.map((m) => (
            <button
              key={m.marketId}
              type="button"
              className="chain-pill"
              aria-pressed={m.collateral === selectedCollateral}
              onClick={() => onSelectCollateral(m.collateral)}
            >
              <span className="chain-pill__glyph">
                <PortalCryptoAvatar ticker={m.collateral} size="sm" />
              </span>
              <span>{m.collateral}</span>
              <span className="chain-pill__sub v-tnum">
                {formatBalanceFr(findGuaranteeBalance(positions, m.collateral))}
              </span>
            </button>
          ))}
        </div>
      </section>

      <section className="brw-section">
        <h4 className="brw-section__title">
          <span className="brw-section__num">2</span>
          <span>Niveau d&apos;emprunt</span>
        </h4>
        {!showCapacityGrid ? (
          <p className="m-0 font-ui text-[13px] text-v-fg-muted">Calcul de votre capacité…</p>
        ) : (
          <div
            className={cn('brw-grid', capacityRefreshing && 'brw-grid--refreshing')}
            aria-busy={capacityRefreshing}
          >
            <div className="brw-grid__dial">
              <PortalLombardRiskDial
                ltv={targetLtvPercent}
                zone={zone}
                maxLtv={dialMaxLtv}
                onLtvChange={onTargetLtvChange}
                disabled={capacityLoading && !capacity}
              />
            </div>
            <div className="brw-grid__panel" style={{ borderColor: zone.color }}>
              <div className="brw-stat">
                <span className="brw-stat__k">Risque de liquidation</span>
                <div className="brw-stat__split">
                  <div>
                    <p className="brw-stat__v" style={{ color: zone.color }}>
                      −<span className="v-tnum">{formatBorrowAmountFr(liquidation.dropPercent, 0)}</span>&nbsp;%
                    </p>
                    <p className="brw-stat__sub">chute max. avant liquidation</p>
                  </div>
                  <div>
                    <p className="brw-stat__v">
                      {liquidation.priceUsdc != null ? (
                        <>
                          <span className="v-tnum">{formatBorrowAmountFr(liquidation.priceUsdc, 0)}</span>&nbsp;USDC
                        </>
                      ) : (
                        '—'
                      )}
                    </p>
                    <p className="brw-stat__sub">prix de liquidation</p>
                  </div>
                </div>
              </div>
              <p className="brw-zone-blurb" style={{ background: zone.bg, color: zone.color }}>
                {zone.blurb}
              </p>
            </div>
          </div>
        )}
        {capacityError ? (
          <p className="m-0 font-ui text-[13px] text-v-error">{capacityError}</p>
        ) : null}
        {capacityRefreshing ? (
          <p className="m-0 font-ui text-[12px] text-v-fg-muted">Mise à jour de la capacité…</p>
        ) : null}
      </section>

      <section className="brw-section">
        <h4 className="brw-section__title">
          <span className="brw-section__num">3</span>
          <span>Montant à emprunter</span>
        </h4>
        <div className="brw-amount-row">
          <div className="chain-field brw-amount-row__field">
            <div className="chain-amt">
              <input
                id="portal-brw-amount"
                type="text"
                inputMode="decimal"
                value={borrowAmount}
                onChange={(e) => onBorrowAmountChange(e.target.value)}
                className="chain-amt__input"
                placeholder="0,00"
              />
              <span className="chain-amt__unit">USDC</span>
              <button
                type="button"
                className="btn--max"
                onClick={() => {
                  if (maxBorrowNum > 0) {
                    onBorrowAmountChange(formatBorrowAmountFr(Math.floor(maxBorrowNum)))
                  }
                }}
              >
                Max
              </button>
            </div>
            {tooMuch ? (
              <span className="chain-field__hint chain-field__hint--ko">
                <KalaiIcon name="info" size={16} />
                Le montant dépasse le maximum empruntable
              </span>
            ) : (
              <span className="chain-field__hint chain-field__hint--soft">
                Max. {formatLombardUsdAmount(capacity?.maxBorrowAmount ?? '0')} USDC à ce niveau d&apos;emprunt.
              </span>
            )}
          </div>

          <aside
            className={cn('brw-collat-box', quoteRefreshing && 'brw-collat-box--refreshing')}
            aria-live="polite"
            aria-busy={quoteRefreshing}
          >
            <span className="brw-collat-box__k">Garantie à déposer</span>
            {quote && numericAmount > 0 ? (
              <>
                <p className="brw-collat-box__v v-tnum">
                  {quote.guaranteeAmount}
                  <span>{quote.collateral}</span>
                </p>
                <p className="brw-collat-box__sub v-tnum">
                  bloqués sur {VANCELIAN_LOMBARD_V1.poweredByLabel}
                  {quoteRefreshing ? ' · mise à jour…' : ''}
                </p>
              </>
            ) : quoteLoading && numericAmount > 0 && apiBorrowAmount ? (
              <>
                {guaranteeEstimate ? (
                  <>
                    <p className="brw-collat-box__v v-tnum">
                      {guaranteeEstimate.guaranteeAmount}
                      <span>{guaranteeEstimate.collateral}</span>
                    </p>
                    <p className="brw-collat-box__sub v-tnum">Calcul du devis Morpho…</p>
                  </>
                ) : (
                  <p className="brw-collat-box__empty">Calcul de la garantie…</p>
                )}
              </>
            ) : guaranteeEstimate && numericAmount > 0 && apiBorrowAmount ? (
              <>
                <p className="brw-collat-box__v v-tnum">
                  ≈ {guaranteeEstimate.guaranteeAmount}
                  <span>{guaranteeEstimate.collateral}</span>
                </p>
                <p className="brw-collat-box__sub v-tnum">
                  {quoteError
                    ? 'Estimation — devis Morpho indisponible'
                    : 'Estimation — confirmation au devis Morpho'}
                </p>
              </>
            ) : (
              <p className="brw-collat-box__empty">
                Saisissez un montant pour voir la garantie nécessaire.
              </p>
            )}
          </aside>
        </div>
        {quoteError ? <p className="m-0 font-ui text-[13px] text-v-error">{quoteError}</p> : null}
      </section>

      <button
        type="button"
        className={`brw-more-toggle ${showDetails ? 'is-open' : ''}`}
        onClick={() => setShowDetails((v) => !v)}
        aria-expanded={showDetails}
      >
        <span>{showDetails ? 'Masquer les détails' : 'Plus de détails'}</span>
        <KalaiIcon name="chevron-down" size={16} className="brw-more-toggle__chv" />
      </button>

      {showDetails ? (
        <div className="brw-details">
          <div className="brw-details__row">
            <span className="k">Marché</span>
            <span className="v">
              {VANCELIAN_LOMBARD_V1.poweredByLabel} · {selectedCollateral} → USDC
            </span>
          </div>
          <div className="brw-details__row">
            <span className="k">Seuil de liquidation</span>
            <span className="v v-tnum">{lltvPercent} %</span>
          </div>
          <div className="brw-details__row">
            <span className="k">Taux d&apos;intérêt</span>
            <span className="v v-tnum">{apyLabel.replace(' variable', '')} · variable</span>
          </div>
          <div className="brw-details__row">
            <span className="k">Frais d&apos;ouverture</span>
            <span className="v">Aucun</span>
          </div>
          <div className="brw-details__row">
            <span className="k">Durée</span>
            <span className="v">Libre · remboursement à votre rythme</span>
          </div>
        </div>
      ) : null}

      <div className="brw-foot">
        <button type="button" className="btn btn--ghost btn--lg" onClick={onBack}>
          Retour
        </button>
        <button
          type="button"
          className="btn btn--primary btn--lg brw-foot__cta"
          disabled={!canContinue}
          onClick={onContinue}
        >
          Continuer
        </button>
      </div>
    </div>
  )
}
