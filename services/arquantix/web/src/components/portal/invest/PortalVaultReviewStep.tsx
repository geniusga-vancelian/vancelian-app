'use client'

import { useMemo } from 'react'

import { TransactionConfirmStepsPreview } from '@/components/portal/transaction/TransactionConfirmStepsPreview'
import { TransactionReviewPage } from '@/components/portal/transaction/TransactionReviewPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import {
  buildVaultReviewPreviewSteps,
  buildVaultTechnicalDetailRows,
  type VaultProcessingContext,
} from '@/components/portal/transaction/mappers/vaultSteps'
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
  processingContext: VaultProcessingContext
}

type Props = {
  context: PortalVaultReviewContext
  onConfirm: () => void
  onBack: () => void
}

/** Vault Review — handoff InvestConfirm, sans exécution (R4.5-D). */
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
    processingContext,
  } = context

  const amountLabel = invFmtAmount(amount, amount % 1 === 0 ? 0 : 2)
  const isDeposit = operation === 'deposit'
  const integrationLabel = getPortalDefiIntegrationLabel(integrationMode)

  const previewSteps = useMemo(
    () => buildVaultReviewPreviewSteps(operation, processingContext),
    [operation, processingContext],
  )

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

  const summaryRows = useMemo(() => {
    const rows: Array<{ k: string; v: string; accent?: boolean }> = [
      {
        k: isDeposit ? VAULT_REVIEW_UI.youInvest : VAULT_REVIEW_UI.youWithdraw,
        v: `${amountLabel} ${assetSymbol}`,
      },
      { k: VAULT_REVIEW_UI.vault, v: target.name },
    ]
    if (isDeposit) {
      rows.push({ k: VAULT_REVIEW_UI.targetYield, v: yieldDisplay })
    }
    rows.push({ k: VAULT_REVIEW_UI.network, v: VAULT_REVIEW_UI.networkLabel })
    rows.push({ k: VAULT_REVIEW_UI.vancelianFees, v: VAULT_REVIEW_UI.vancelianFeesWaived, accent: true })
    return rows
  }, [amountLabel, assetSymbol, isDeposit, target.name, yieldDisplay])

  const confirmCta = isDeposit ? VAULT_REVIEW_UI.confirmDeposit : VAULT_REVIEW_UI.confirmWithdraw

  const lead = isDeposit ? (
    <>
      Vous êtes sur le point d&apos;investir{' '}
      <b className="v-tnum">
        {amountLabel} {assetSymbol}
      </b>{' '}
      sur {target.short}. Vérifiez les détails avant de lancer la transaction.
    </>
  ) : (
    <>
      Vous êtes sur le point de retirer{' '}
      <b className="v-tnum">
        {amountLabel} {assetSymbol}
      </b>{' '}
      depuis {target.short}. Vérifiez les détails avant de lancer.
    </>
  )

  return (
    <TransactionReviewPage
      title={VAULT_REVIEW_UI.title}
      layout="confirm"
      onBack={onBack}
      onClose={onBack}
      backButtonLabel={VAULT_REVIEW_UI.modifierCta}
      primaryAction={{
        label: confirmCta,
        onClick: onConfirm,
      }}
    >
      <p className="inv-confirm__lead">{lead}</p>

      <div className="inv-summary inv-confirm__sum">
        {summaryRows.map((row) => (
          <div className="inv-summary__row" key={row.k}>
            <span className="k">{row.k}</span>
            <span className={`v${row.accent ? ' v--accent' : ''}`}>{row.v}</span>
          </div>
        ))}
      </div>

      <TransactionConfirmStepsPreview steps={previewSteps} />

      <TransactionTechnicalDetails rows={techRows} title={VAULT_REVIEW_UI.technicalDetailsTitle} />
    </TransactionReviewPage>
  )
}
