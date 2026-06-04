/**
 * Mapper Vault Morpho / Ledgity → Transaction UX Framework V1 (R4.5-D).
 */
import type { PortalVaultExecutionPhase, PortalVaultOperation } from '@/lib/portal/vaultFlowTypes'
import { VAULT_FLOW_UI } from '@/components/portal/transaction/mappers/vaultUiCopy'
import type { TransactionStep, TransactionTerminalFailureCopy } from '@/components/portal/transaction/types'
import type { TransactionTechnicalDetailsRow } from '@/components/portal/transaction/types'

export const VAULT_DEPOSIT_PROCESSING_STEP_DEFS: Array<{
  label: string
  defaultSub: (ctx: VaultProcessingContext) => string
}> = [
  {
    label: 'Autorisation du paiement',
    defaultSub: (ctx) =>
      `Débit de ${ctx.amountLabel} depuis votre compte et préparation de l’opération.`,
  },
  {
    label: 'Exécution de l’ordre',
    defaultSub: (ctx) => `Placement de ${ctx.amountLabel} sur ${ctx.vaultLabel}.`,
  },
  {
    label: 'Dépôt on-chain',
    defaultSub: () => 'Confirmez la transaction dans votre portefeuille si demandé.',
  },
  {
    label: 'Réception dans votre portefeuille',
    defaultSub: () => 'Votre position dans le coffre est mise à jour.',
  },
]

export const VAULT_WITHDRAW_PROCESSING_STEP_DEFS: Array<{
  label: string
  defaultSub: (ctx: VaultProcessingContext) => string
}> = [
  {
    label: 'Préparation',
    defaultSub: () => 'Vérification de votre position et préparation du retrait.',
  },
  {
    label: 'Validation du retrait',
    defaultSub: () => 'Confirmez l’opération dans votre portefeuille.',
  },
  {
    label: 'Retrait du coffre',
    defaultSub: (ctx) => `Retrait de ${ctx.amountLabel} depuis ${ctx.vaultLabel}.`,
  },
  {
    label: 'Mise à jour du portefeuille',
    defaultSub: () => 'Synchronisation de votre solde.',
  },
]

export type VaultProcessingContext = {
  amountLabel: string
  vaultLabel: string
  assetSymbol: string
}

export const VAULT_PROCESSING_COMPLETED_INDEX = 4

export const VAULT_TERMINAL_FAILURE_COPY: TransactionTerminalFailureCopy = {
  title: 'Impossible d’effectuer l’opération',
  lines: ['Aucun mouvement n’a été réalisé.'],
}

const FORBIDDEN_USER_PATTERN =
  /revert|retryable_failed|group_key|idempotency|vault_transaction_id|approval pending|confirming on-chain|tx reverted|0x[a-fA-F0-9]{8,}/i

export function vaultProcessingStepperIndex(phase: PortalVaultExecutionPhase): number {
  switch (phase) {
    case 'preparing':
      return 0
    case 'approval_pending':
      return 1
    case 'deposit_pending':
    case 'withdraw_pending':
      return 2
    case 'confirming':
      return 3
    case 'confirmed':
      return 4
    default:
      return 0
  }
}

export function buildVaultProcessingSteps(
  operation: PortalVaultOperation,
  ctx: VaultProcessingContext,
): TransactionStep[] {
  const defs =
    operation === 'deposit' ? VAULT_DEPOSIT_PROCESSING_STEP_DEFS : VAULT_WITHDRAW_PROCESSING_STEP_DEFS
  return defs.map((step) => ({
    label: step.label,
    subtext: step.defaultSub(ctx),
  }))
}

/** Preview accordéon — écran Confirmation (handoff InvestConfirm). */
export function buildVaultReviewPreviewSteps(
  operation: PortalVaultOperation,
  ctx: VaultProcessingContext,
): TransactionStep[] {
  return buildVaultProcessingSteps(operation, ctx)
}

export function buildVaultSuccessSteps(
  operation: PortalVaultOperation,
  ctx: VaultProcessingContext,
): Array<{ name: string; body: string }> {
  return buildVaultProcessingSteps(operation, ctx).map((step) => ({
    name: step.label,
    body: step.subtext,
  }))
}

export function buildVaultSuccessSummary(
  operation: PortalVaultOperation,
  ctx: VaultProcessingContext,
  yieldPct: number,
): Array<{ k: string; v: string }> {
  const rows: Array<{ k: string; v: string }> = [
    {
      k: operation === 'deposit' ? 'Montant placé' : 'Montant retiré',
      v: ctx.amountLabel,
    },
    { k: 'Coffre', v: ctx.vaultLabel },
  ]
  if (operation === 'deposit' && yieldPct > 0) {
    rows.push({
      k: 'Rendement cible',
      v: `${(yieldPct * 100).toLocaleString('fr-FR', {
        minimumFractionDigits: 1,
        maximumFractionDigits: 2,
      })} % / an`,
    })
  }
  rows.push({ k: 'Frais Vancelian', v: 'Offerts' })
  rows.push({ k: 'Réseau', v: 'Base' })
  return rows
}

export function resolveVaultFailureCopy(error: unknown): TransactionTerminalFailureCopy {
  if (error == null) {
    return VAULT_TERMINAL_FAILURE_COPY
  }
  const msg = error instanceof Error ? error.message : String(error)
  if (FORBIDDEN_USER_PATTERN.test(msg)) {
    return VAULT_TERMINAL_FAILURE_COPY
  }
  if (
    /Transaction revert|Receipt introuvable|Confirmation ledger|Operation failed|échoué/i.test(msg)
  ) {
    return VAULT_TERMINAL_FAILURE_COPY
  }
  return {
    title: VAULT_TERMINAL_FAILURE_COPY.title,
    lines: [msg, VAULT_TERMINAL_FAILURE_COPY.lines[0]!],
  }
}

export function buildVaultTechnicalDetailRows(args: {
  vaultAddress: string
  providerLabel: string
  integrationLabel: string
  sourceAsset: string
  receivedAsset: string
  disclaimer?: string
  txHash?: string | null
}): TransactionTechnicalDetailsRow[] {
  const rows: TransactionTechnicalDetailsRow[] = [
    { label: 'Réseau', value: 'Base' },
    { label: 'Protocole', value: args.integrationLabel },
    { label: 'Fournisseur', value: args.providerLabel },
    { label: 'Actif source', value: args.sourceAsset },
    { label: 'Actif reçu', value: args.receivedAsset },
    { label: 'Contrat coffre', value: args.vaultAddress },
  ]
  if (args.disclaimer?.trim()) {
    rows.push({ label: 'Avertissement', value: args.disclaimer.trim() })
  }
  if (args.txHash?.trim()) {
    rows.push({ label: 'Hash de transaction', value: args.txHash.trim() })
  }
  return rows
}

export function vaultSuccessCopy(operation: PortalVaultOperation): {
  title: string
} {
  return {
    title:
      operation === 'deposit'
        ? VAULT_FLOW_UI.successDepositTitle
        : VAULT_FLOW_UI.successWithdrawTitle,
  }
}
