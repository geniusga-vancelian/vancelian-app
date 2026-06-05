'use client'

import {
  PortalBundleTargetAllocation,
  type PortalBundleAllocationRow,
} from '@/components/portal/bundles/PortalBundleTargetAllocation'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { BUNDLE_FLOW_UI } from '@/components/portal/transaction/mappers/bundleUiCopy'
import { formatBundleUsdcAmount } from '@/lib/portal/bundleFormat'

type Props = {
  bundleTitle: string
  entryOptions: string[]
  fundingAsset: string
  amount: string
  targetAllocationRows: PortalBundleAllocationRow[]
  portfolioReady: boolean
  setupError: string | null
  setupDisabled: boolean
  minFundingHint: string
  onFundingAssetChange: (asset: string) => void
  onAmountChange: (value: string) => void
  onContinue: () => void
  onClose: () => void
}

/** Setup invest bundle — inv-pane + allocation cible théorique (handoff InvestForm panier). */
export function PortalBundleInvestSetup({
  bundleTitle,
  entryOptions,
  fundingAsset,
  amount,
  targetAllocationRows,
  portfolioReady,
  setupError,
  setupDisabled,
  minFundingHint,
  onFundingAssetChange,
  onAmountChange,
  onContinue,
  onClose,
}: Props) {
  return (
    <div className="inv-pane">
      <header className="inv-head">
        <h2 className="inv-head__title">{BUNDLE_FLOW_UI.setupTitle(bundleTitle)}</h2>
        <div className="inv-head__actions">
          <button type="button" className="inv-head__btn" onClick={onClose} aria-label="Fermer">
            <KalaiIcon name="close" size={16} />
          </button>
        </div>
      </header>

      <p className="inv-confirm__lead" style={{ marginTop: 0 }}>
        {BUNDLE_FLOW_UI.setupLead(bundleTitle)}
      </p>

      {!portfolioReady ? (
        <p className="inv-alert">
          Ce panier n&apos;est pas encore provisionné sur votre compte. Rechargez la page Marchés.
        </p>
      ) : null}

      <div className="inv-iowrap">
        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">Je place</span>
            <span className="inv-io__balance">Stablecoin · entrée du panier</span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              inputMode="decimal"
              className="inv-io__amount"
              value={amount}
              onChange={(e) => onAmountChange(e.target.value)}
              disabled={!portfolioReady}
              aria-label="Montant à investir"
              placeholder="0"
            />
            <div className="inv-chip" style={{ pointerEvents: portfolioReady ? 'auto' : 'none' }}>
              <span className="inv-chip__ic" style={{ background: '#2775CA', color: '#fff' }}>
                $
              </span>
              <span className="inv-chip__meta">
                <span className="inv-chip__name">{fundingAsset}</span>
                <span className="inv-chip__unit">Entrée autorisée</span>
              </span>
              {entryOptions.length > 1 ? (
                <select
                  className="sr-only"
                  value={fundingAsset}
                  onChange={(e) => onFundingAssetChange(e.target.value)}
                  aria-label="Actif d'entrée"
                  tabIndex={-1}
                >
                  {entryOptions.map((asset) => (
                    <option key={asset} value={asset}>
                      {asset}
                    </option>
                  ))}
                </select>
              ) : null}
            </div>
          </div>
          {entryOptions.length > 1 ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {entryOptions.map((asset) => (
                <button
                  key={asset}
                  type="button"
                  className={`rounded-full border px-3 py-1 font-ui text-[12px] ${
                    fundingAsset === asset
                      ? 'border-v-fg bg-v-fg text-v-bg'
                      : 'border-v-border text-v-fg-muted'
                  }`}
                  onClick={() => onFundingAssetChange(asset)}
                  disabled={!portfolioReady}
                >
                  {asset}
                </button>
              ))}
            </div>
          ) : null}
          <p className="inv-io__balance">{minFundingHint}</p>
        </div>

        <div className="inv-divider" aria-hidden="true" />

        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">Je reçois</span>
            <span className="inv-io__balance">{bundleTitle}</span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              className="inv-io__amount"
              value={amount ? formatBundleUsdcAmount(Number(amount) || amount) : '0'}
              readOnly
              aria-label="Répartition panier"
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
                <span className="inv-chip__unit">Allocation cible</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {targetAllocationRows.length > 0 ? (
        <PortalBundleTargetAllocation
          rows={targetAllocationRows}
          title={BUNDLE_FLOW_UI.targetAllocationSetup}
        />
      ) : null}

      <div className="inv-summary">
        <div className="inv-summary__row">
          <span className="k">Frais Vancelian</span>
          <span className="v v--accent">Offerts</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">Réseau</span>
          <span className="v">Base</span>
        </div>
      </div>

      {setupError ? <p className="inv-feedback inv-feedback--error">{setupError}</p> : null}

      <button
        type="button"
        className="btn btn--primary btn--lg inv-cta"
        disabled={setupDisabled}
        onClick={onContinue}
      >
        {BUNDLE_FLOW_UI.continueCta}
      </button>
    </div>
  )
}
