/**
 * Copy produit Vault deposit / withdraw (FR) — aligné handoff InvestConfirm / swap (R4.5-D).
 */
export const VAULT_FORBIDDEN_PRIMARY_JARGON =
  /approval pending|confirming on-chain|tx reverted|tx hash|group_key|idempotency|vault_transaction_id|0x[a-fA-F0-9]{8,}/i

export const VAULT_REVIEW_UI = {
  title: 'Confirmation',
  confirmDeposit: "Confirmer l'investissement",
  confirmWithdraw: 'Confirmer le retrait',
  modifierCta: 'Modifier',
  youInvest: 'Montant investi',
  youWithdraw: 'Montant retiré',
  vault: 'Coffre',
  targetYield: 'Rendement cible',
  network: 'Réseau',
  vancelianFees: 'Frais Vancelian',
  vancelianFeesWaived: 'Offerts',
  networkLabel: 'Base',
  technicalDetailsTitle: 'Détails techniques',
} as const

export const VAULT_FLOW_UI = {
  setupTitleInvest: 'Investir',
  setupTitleWithdraw: 'Retirer',
  continueCta: 'Continuer',
  processingTitle: 'Opération en cours',
  processingLeadDeposit: (amountLabel: string, vaultLabel: string) =>
    `Votre investissement de ${amountLabel} sur ${vaultLabel} est en cours d'exécution. Ne fermez pas cette fenêtre.`,
  processingLeadWithdraw: (amountLabel: string, vaultLabel: string) =>
    `Votre retrait de ${amountLabel} depuis ${vaultLabel} est en cours d'exécution. Ne fermez pas cette fenêtre.`,
  successDepositTitle: 'Investissement effectué',
  successWithdrawTitle: 'Retrait effectué',
  successStepsTitleDeposit: 'Étapes de votre investissement',
  successStepsTitleWithdraw: 'Étapes de votre retrait',
  successSummaryTitle: 'Récapitulatif',
  successNoteDeposit:
    'Le rendement est versé au fil de l’eau. Vous suivez la performance de votre placement depuis votre portefeuille.',
  successNoteWithdraw:
    'Les fonds sont disponibles sur votre compte. Vous pouvez les réinvestir ou les conserver.',
  viewVaultCta: 'Voir mon coffre',
  preparingSecureConfirmation: 'Préparation de la confirmation sécurisée…',
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
    VAULT_FLOW_UI.successWithdrawTitle,
    VAULT_FLOW_UI.successStepsTitleDeposit,
    VAULT_FLOW_UI.successStepsTitleWithdraw,
    VAULT_FLOW_UI.successSummaryTitle,
    VAULT_FLOW_UI.successNoteDeposit,
    VAULT_FLOW_UI.successNoteWithdraw,
  ]
}

export function assertNoVaultPrimaryJargon(text: string): void {
  if (VAULT_FORBIDDEN_PRIMARY_JARGON.test(text)) {
    throw new Error(`Vault primary copy must not include jargon: ${text}`)
  }
}
