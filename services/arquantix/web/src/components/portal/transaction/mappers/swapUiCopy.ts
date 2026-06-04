/**
 * Copy utilisateur — flux swap (FR, handoff InvestConfirm / InvestProcessing).
 */
export const SWAP_FORBIDDEN_PRIMARY_JARGON =
  /revert|retryable_failed|group_key|logical_borrow_id|idempotency|lifi|li\.fi|token approval|tx reverted|0x[a-f0-9]{8,}/i

export const SWAP_REVIEW_UI = {
  title: 'Confirmation',
  confirmCta: "Confirmer l'échange",
  modifierCta: 'Modifier',
  youExchange: 'Vous échangez',
  youReceive: 'Vous recevez',
  vancelianFees: 'Frais Vancelian',
  vancelianFeesWaived: 'Offerts',
  exchangeRate: 'Taux',
  minimumReceive: 'Minimum garanti',
  networkFees: 'Frais réseau',
  network: 'Réseau',
  technicalDetailsTitle: 'Détails techniques',
  backButtonAria: 'Retour',
} as const

export const SWAP_FLOW_UI = {
  processingTitle: 'Échange en cours',
  processingLead: (payLabel: string, fromAsset: string, toAsset: string) =>
    `Votre échange de ${payLabel} ${fromAsset} vers ${toAsset} est en cours d'exécution. Ne fermez pas cette fenêtre.`,
  successTitle: 'Échange effectué',
  successLeadReceive: (receiveLabel: string, toAsset: string) => `${receiveLabel} ${toAsset}`,
  successStepsTitle: 'Étapes de votre échange',
  successSummaryTitle: 'Récapitulatif',
  successNote:
    'Vos actifs sont conservés en garde MPC. Vous les retrouvez et les gérez depuis votre portefeuille.',
  viewWalletCta: (toAsset: string) => `Voir mon wallet ${toAsset}`,
  backToWallet: 'Retour au wallet',
  preparingSecureConfirmation: 'Préparation de la confirmation sécurisée…',
  quoteExpiredLine:
    'Votre devis a expiré. Revenez à l’étape montant et demandez une nouvelle estimation.',
  priceChangedLine:
    'Le montant estimé à recevoir a légèrement changé. Vérifiez le récapitulatif puis confirmez à nouveau.',
  priceChangedReviewBanner:
    'Le prix a été mis à jour. Vérifiez les montants avant de confirmer.',
} as const

export const SWAP_RESULT_IMPOSSIBLE_ACTIONS = {
  close: 'Fermer',
  retry: 'Réessayer',
} as const

export function collectSwapReviewPrimaryStrings(): string[] {
  return Object.values(SWAP_REVIEW_UI)
}

export function collectSwapProcessingPrimaryStrings(
  ctx: { fromAsset: string; toAsset: string; payLabel: string; receiveLabel: string },
  steps: Array<{ label: string; subtext: string }>,
): string[] {
  return [
    SWAP_FLOW_UI.processingTitle,
    SWAP_FLOW_UI.processingLead(ctx.payLabel, ctx.fromAsset, ctx.toAsset),
    ...steps.flatMap((s) => [s.label, s.subtext]),
  ]
}

export function assertNoSwapPrimaryJargon(text: string): void {
  if (SWAP_FORBIDDEN_PRIMARY_JARGON.test(text)) {
    throw new Error(`Swap primary copy must not include jargon: ${text}`)
  }
}
