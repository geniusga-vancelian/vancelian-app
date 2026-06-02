/**
 * Copy produit Vault deposit / withdraw (FR) — R4.5-D.
 */
export const VAULT_FORBIDDEN_PRIMARY_JARGON =
  /approval pending|confirming on-chain|tx reverted|tx hash|group_key|idempotency|vault_transaction_id|0x[a-fA-F0-9]{8,}/i

export const VAULT_REVIEW_UI = {
  titleDeposit: 'Récapitulatif du dépôt',
  titleWithdraw: 'Récapitulatif du retrait',
  confirmDeposit: 'Confirmer le dépôt',
  confirmWithdraw: 'Confirmer le retrait',
  youInvest: 'Vous investissez',
  youWithdraw: 'Vous retirez',
  vault: 'Coffre',
  targetYield: 'Rendement cible',
  network: 'Réseau',
  vancelianFees: 'Frais Vancelian',
  vancelianFeesWaived: 'Offerts',
  networkLabel: 'Base',
  backButton: 'Retour',
  technicalDetailsTitle: 'Détails techniques',
  disclaimerRowLabel: 'Avertissement',
} as const

export const VAULT_FLOW_UI = {
  processingTitle: 'Opération en cours',
  processingLeadDeposit: (amountLabel: string, vaultLabel: string) =>
    `Votre dépôt de ${amountLabel} vers ${vaultLabel} est en cours. Ne fermez pas cette fenêtre.`,
  processingLeadWithdraw: (amountLabel: string, vaultLabel: string) =>
    `Votre retrait de ${amountLabel} depuis ${vaultLabel} est en cours. Ne fermez pas cette fenêtre.`,
  successDepositTitle: 'Dépôt effectué',
  successDepositSubtitle: 'Votre position a été mise à jour.',
  successWithdrawTitle: 'Retrait effectué',
  successWithdrawSubtitle: 'Vos fonds sont disponibles.',
  continueCta: 'Voir le récapitulatif',
} as const

export const VAULT_RESULT_IMPOSSIBLE_ACTIONS = {
  close: 'Fermer',
  retry: 'Réessayer',
} as const

export function collectVaultReviewPrimaryStrings(): string[] {
  return Object.values(VAULT_REVIEW_UI)
}

export function collectVaultProcessingPrimaryStrings(
  operation: 'deposit' | 'withdraw',
  steps: Array<{ label: string; subtext: string }>,
  amountLabel: string,
  vaultLabel: string,
): string[] {
  const lead =
    operation === 'deposit'
      ? VAULT_FLOW_UI.processingLeadDeposit(amountLabel, vaultLabel)
      : VAULT_FLOW_UI.processingLeadWithdraw(amountLabel, vaultLabel)
  return [
    VAULT_FLOW_UI.processingTitle,
    lead,
    ...steps.flatMap((s) => [s.label, s.subtext]),
  ]
}

export function collectVaultResultPrimaryStrings(): string[] {
  return [
    VAULT_FLOW_UI.successDepositTitle,
    VAULT_FLOW_UI.successDepositSubtitle,
    VAULT_FLOW_UI.successWithdrawTitle,
    VAULT_FLOW_UI.successWithdrawSubtitle,
  ]
}

export function assertNoVaultPrimaryJargon(text: string): void {
  if (VAULT_FORBIDDEN_PRIMARY_JARGON.test(text)) {
    throw new Error(`Vault primary copy must not include jargon: ${text}`)
  }
}
