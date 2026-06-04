'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { BUNDLE_WITHDRAW_FLOW_UI } from '@/components/portal/transaction/mappers/bundleUiCopy'
import { formatBundleUsdcAmount } from '@/lib/portal/bundleFormat'
import type { BundleHoldingsSplit } from '@/lib/portal/bundleWithdrawFormat'
import { formatCryptoMoney } from '@/lib/portal/cryptoWalletFormat'

type Props = {
  portfolioName: string
  entryAsset: string
  currency: string
  holdings: BundleHoldingsSplit
  maxAmount: number
  fullWithdraw: boolean
  amount: string
  setupError: string | null
  setupDisabled: boolean
  resumeHint: string | null
  onFullWithdrawChange: (value: boolean) => void
  onAmountChange: (value: string) => void
  onApplyMax: () => void
  onResume?: () => void
  onContinue: () => void
  onClose: () => void
}

/** Setup retrait bundle — inv-pane, destination USDC (pas d’allocation cible). */
export function PortalBundleWithdrawSetup({
  portfolioName,
  entryAsset,
  currency,
  holdings,
  maxAmount,
  fullWithdraw,
  amount,
  setupError,
  setupDisabled,
  resumeHint,
  onFullWithdrawChange,
  onAmountChange,
  onApplyMax,
  onResume,
  onContinue,
  onClose,
}: Props) {
  const displayAmount = fullWithdraw
    ? formatCryptoMoney(maxAmount, currency)
    : amount
      ? formatBundleUsdcAmount(Number(amount) || amount)
      : '0'

  return (
    <div className="inv-pane">
      <header className="inv-head">
        <h2 className="inv-head__title">{BUNDLE_WITHDRAW_FLOW_UI.setupTitle()}</h2>
        <div className="inv-head__actions">
          <button type="button" className="inv-head__btn" onClick={onClose} aria-label="Fermer">
            <KalaiIcon name="close" size={16} />
          </button>
        </div>
      </header>

      <p className="inv-confirm__lead" style={{ marginTop: 0 }}>
        {BUNDLE_WITHDRAW_FLOW_UI.setupLead(portfolioName)}
      </p>

      {resumeHint && onResume ? (
        <div className="inv-alert">
          <p className="m-0">{resumeHint}</p>
          <button type="button" className="btn btn--secondary btn--sm mt-2" onClick={onResume}>
            Reprendre le retrait
          </button>
        </div>
      ) : null}

      <div className="inv-iowrap">
        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">Je retire</span>
            <span className="inv-io__balance">{portfolioName}</span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              inputMode="decimal"
              className="inv-io__amount"
              value={fullWithdraw ? displayAmount : amount}
              onChange={(e) => onAmountChange(e.target.value)}
              disabled={setupDisabled || fullWithdraw}
              aria-label="Montant à retirer"
              placeholder="0"
            />
            <div className="inv-chip">
              <span
                className="inv-chip__ic"
                style={{
                  background:
                    "url('/app-ds/assets/photos/coffre-flex.png') center/cover no-repeat",
                  color: '#F4F1E8',
                }}
              />
              <span className="inv-chip__meta">
                <span className="inv-chip__name">Panier</span>
                <span className="inv-chip__unit">Disponible</span>
              </span>
            </div>
          </div>
          {!fullWithdraw && maxAmount > 0 ? (
            <button
              type="button"
              className="inv-io__max mt-1 border-0 bg-transparent p-0 font-ui text-[12px] text-v-blue underline"
              onClick={onApplyMax}
            >
              Max · {formatCryptoMoney(maxAmount, currency)}
            </button>
          ) : null}
        </div>

        <div className="inv-divider" aria-hidden="true" />

        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">Je reçois</span>
            <span className="inv-io__balance">Mon Trading</span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              className="inv-io__amount"
              value={displayAmount}
              readOnly
              aria-label="Montant reçu"
            />
            <div className="inv-chip">
              <span className="inv-chip__ic" style={{ background: '#2775CA', color: '#fff' }}>
                $
              </span>
              <span className="inv-chip__meta">
                <span className="inv-chip__name">{entryAsset}</span>
                <span className="inv-chip__unit">Portefeuille trading</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="inv-summary">
        <div className="inv-summary__row">
          <span className="k">Cash leg ({entryAsset})</span>
          <span className="v v-tnum">
            {formatBundleUsdcAmount(holdings.cashLegQuantity)} {entryAsset}
          </span>
        </div>
        <div className="inv-summary__row">
          <span className="k">Actifs alloués (estim.)</span>
          <span className="v">{formatCryptoMoney(holdings.spotNotional, currency)}</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">Réseau</span>
          <span className="v">Base</span>
        </div>
      </div>

      <label className="flex cursor-pointer items-center gap-2 font-ui text-[13px] text-v-fg">
        <input
          type="checkbox"
          checked={fullWithdraw}
          onChange={(e) => onFullWithdrawChange(e.target.checked)}
          disabled={setupDisabled}
        />
        Retrait total
      </label>

      <p className="m-0 font-ui text-[12px] text-v-fg-muted">{BUNDLE_WITHDRAW_FLOW_UI.releasePendingNote}</p>

      {setupError ? <p className="inv-feedback inv-feedback--error">{setupError}</p> : null}

      <button
        type="button"
        className="btn btn--primary btn--lg inv-cta"
        disabled={setupDisabled}
        onClick={onContinue}
      >
        {BUNDLE_WITHDRAW_FLOW_UI.continueCta}
      </button>
    </div>
  )
}
