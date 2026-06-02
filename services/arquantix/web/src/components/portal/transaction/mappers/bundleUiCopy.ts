/**
 * Copy produit Bundle invest (FR) — R4.5-E.
 */
export const BUNDLE_FORBIDDEN_PRIMARY_JARGON =
  /\bLI\.FI\b|\bLeg\b|\bBatch\b|\bPrivy\b|bundle_internal_swap|group_key|idempotency|tx reverted|0x[a-fA-F0-9]{8,}/i

export const BUNDLE_REVIEW_UI = {
  title: 'Récapitulatif de l’investissement',
  confirmCta: 'Confirmer l’investissement',
  youInvest: 'Vous investissez',
  bundle: 'Bundle',
  targetAllocation: 'Allocation cible',
  network: 'Réseau',
  networkLabel: 'Base',
  vancelianFees: 'Frais Vancelian',
  vancelianFeesWaived: 'Offerts',
  liquidity: 'Liquidité',
  liquidityPilot: 'Selon disponibilité marché',
  backButton: 'Retour',
  technicalDetailsTitle: 'Détails techniques',
  previewWarningTitle: 'Avertissements',
} as const

export const BUNDLE_FLOW_UI = {
  setupTitle: (bundleTitle: string) => `Investir — ${bundleTitle}`,
  setupLead: 'Choisissez le montant et vérifiez l’allocation cible avant de confirmer.',
  continueCta: 'Voir le récapitulatif',
  walletConnecting: 'Connexion du portefeuille en cours…',
  targetAllocationSetup: 'Allocation cible (estimation)',
  estimatedEntry: 'Entrée estimée',
  processingTitle: 'Investissement en cours',
  processingLead: (amountLabel: string, bundleLabel: string) =>
    `Votre investissement de ${amountLabel} vers ${bundleLabel} est en cours. Ne fermez pas cette fenêtre.`,
  successTitle: 'Portefeuille créé',
  successSubtitle: 'Votre allocation a été mise à jour.',
  viewBasketCta: 'Voir mon panier',
  partialPreviewNote:
    'Certains actifs peuvent ne pas être entièrement disponibles — l’allocation pourrait être partielle.',
} as const

export const BUNDLE_TERMINAL_IMPOSSIBLE = {
  title: 'Impossible de finaliser l’investissement',
  lines: ['Aucun portefeuille n’a été modifié.'],
} as const

export const BUNDLE_TERMINAL_RECONCILIATION = {
  title: 'Vérification nécessaire',
  lines: ['Votre opération est en cours de réconciliation.'],
} as const

export const BUNDLE_RESULT_ACTIONS = {
  close: 'Fermer',
  retry: 'Réessayer',
} as const

export const BUNDLE_WITHDRAW_PROCESSING_STEPS = {
  step1: 'Préparation du retrait',
  step2: 'Désallocation du portefeuille',
  step3: 'Transfert des fonds',
  step4: 'Mise à jour du portefeuille',
} as const

export function collectBundleReviewPrimaryStrings(): string[] {
  return Object.values(BUNDLE_REVIEW_UI)
}

export function collectBundleProcessingPrimaryStrings(
  steps: Array<{ label: string; subtext: string }>,
  lead: string,
): string[] {
  return [BUNDLE_FLOW_UI.processingTitle, lead, ...steps.flatMap((s) => [s.label, s.subtext])]
}

export function collectBundleResultPrimaryStrings(): string[] {
  return [
    BUNDLE_FLOW_UI.successTitle,
    BUNDLE_FLOW_UI.successSubtitle,
    BUNDLE_TERMINAL_IMPOSSIBLE.title,
    BUNDLE_TERMINAL_IMPOSSIBLE.lines[0]!,
    BUNDLE_TERMINAL_RECONCILIATION.title,
    BUNDLE_TERMINAL_RECONCILIATION.lines[0]!,
  ]
}

export function assertNoBundlePrimaryJargon(text: string): void {
  if (BUNDLE_FORBIDDEN_PRIMARY_JARGON.test(text)) {
    throw new Error(`Bundle primary copy must not include jargon: ${text}`)
  }
}
