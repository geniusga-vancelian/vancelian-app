'use client'

import { useMemo } from 'react'

import { PortalInvestChip } from '@/components/portal/invest/PortalInvestFlowParts'
import { TransactionReviewPage } from '@/components/portal/transaction/TransactionReviewPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import { buildVaultTechnicalDetailRows } from '@/components/portal/transaction/mappers/vaultSteps'
import { VAULT_REVIEW_UI } from '@/components/portal/transaction/mappers/vaultUiCopy'
import { getPortalDefiIntegrationLabel } from '@/lib/portal/morphoConstants'
import type { PortalInvestSource, PortalInvestTarget } from '@/lib/portal/portalInvestFlowFormat'
import { invFmtAmount } from '@/lib/portal/portalInvestFlowFormat'
import type { PortalVaultOperation } from '@/lib/portal/vaultFlowTypes'

export type PortalVaultReviewContext = {
  operation: PortalVaultOperation
  amount: number
  assetSymbol: string
  source: PortalInvestSource
  target: PortalInvestTarget
  vaultAddress: string
  provider: string
  integrationMode: 'direct_morpho' | 'ledgity_vault'
  disclaimer?: string
  yieldPct: number
}

type Props = {
  context: PortalVaultReviewContext
  onConfirm: () => void
  onBack: () => void
}

/** Vault Review — récap uniquement, pas d’exécution (R4.5-D). */
export function PortalVaultReviewStep({ context, onConfirm, onBack }: Props) {
  const {
    operation,
    amount,
    assetSymbol,
    source,
    target,
    vaultAddress,
    provider,
    integrationMode,
    disclaimer,
    yieldPct,
  } = context

  const amountLabel = invFmtAmount(amount, amount % 1 === 0 ? 0 : 2)
  const isDeposit = operation === 'deposit'
  const integrationLabel = getPortalDefiIntegrationLabel(integrationMode)

  const techRows = useMemo(
    () =>
      buildVaultTechnicalDetailRows({
        vaultAddress,
        providerLabel: provider,
        integrationLabel,
        sourceAsset: source.techSource,
        receivedAsset: target.tech,
        disclaimer,
      }),
    [disclaimer, integrationLabel, provider, source.techSource, target.tech, vaultAddress],
  )

  const yieldDisplay =
    yieldPct > 0
      ? `${(yieldPct * 100).toLocaleString('fr-FR', {
          minimumFractionDigits: 1,
          maximumFractionDigits: 2,
        })} % / an`
      : '—'

  return (
    <TransactionReviewPage
      title={isDeposit ? VAULT_REVIEW_UI.titleDeposit : VAULT_REVIEW_UI.titleWithdraw}
      onBack={onBack}
      onClose={onBack}
      backButtonLabel={VAULT_REVIEW_UI.backButton}
      primaryAction={{
        label: isDeposit ? VAULT_REVIEW_UI.confirmDeposit : VAULT_REVIEW_UI.confirmWithdraw,
        onClick: onConfirm,
      }}
    >
      <div className="inv-summary">
        <div className="inv-summary__row">
          <span className="k">{isDeposit ? VAULT_REVIEW_UI.youInvest : VAULT_REVIEW_UI.youWithdraw}</span>
          <span className="v">
            {amountLabel} {assetSymbol}
          </span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{VAULT_REVIEW_UI.vault}</span>
          <span className="v">{target.name}</span>
        </div>
        {isDeposit ? (
          <div className="inv-summary__row">
            <span className="k">{VAULT_REVIEW_UI.targetYield}</span>
            <span className="v">{yieldDisplay}</span>
          </div>
        ) : null}
        <div className="inv-summary__row">
          <span className="k">{VAULT_REVIEW_UI.network}</span>
          <span className="v">{VAULT_REVIEW_UI.networkLabel}</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{VAULT_REVIEW_UI.vancelianFees}</span>
          <span className="v v--accent">{VAULT_REVIEW_UI.vancelianFeesWaived}</span>
        </div>
      </div>

      <div className="inv-iowrap inv-iowrap--compact">
        <div className="inv-io">
          <div className="inv-io__row">
            <input
              type="text"
              className="inv-io__amount"
              value={amountLabel}
              readOnly
              aria-label={isDeposit ? VAULT_REVIEW_UI.youInvest : VAULT_REVIEW_UI.youWithdraw}
            />
            <PortalInvestChip asset={isDeposit ? source : target} selectable={false} />
          </div>
        </div>
      </div>

      <TransactionTechnicalDetails rows={techRows} title={VAULT_REVIEW_UI.technicalDetailsTitle} />
    </TransactionReviewPage>
  )
}
