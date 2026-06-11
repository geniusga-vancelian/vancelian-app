/**
 * Copy produit Bundle invest (FR) — R4.5-E.
 */
import type { TransactionTerminalFailureCopy } from '@/components/portal/transaction/types'

export const BUNDLE_FORBIDDEN_PRIMARY_JARGON =
  /\bLI\.FI\b|\bLeg\b|\bBatch\b|\bPrivy\b|bundle_internal_swap|group_key|idempotency|tx reverted|0x[a-fA-F0-9]{8,}/i

export const BUNDLE_REVIEW_UI = {
  title: 'Confirmation',
  confirmCta: 'Confirmer l’investissement',
  modifierCta: 'Modifier',
  youInvest: 'Montant investi',
  bundle: 'Panier',
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
  setupTitle: (bundleTitle: string) => `Investir`,
  setupLead: (bundleTitle: string) =>
    `Placez des fonds sur ${bundleTitle}. Vérifiez l’allocation cible avant de confirmer.`,
  continueCta: 'Continuer',
  preparingSecureConfirmation: 'Préparation de la confirmation sécurisée…',
  walletConnecting: 'Connexion du portefeuille en cours…',
  targetAllocationSetup: 'Allocation cible',
  estimatedEntry: 'Entrée estimée',
  processingTitle: 'Investissement en cours',
  processingLead: (amountLabel: string, bundleLabel: string) =>
    `Votre investissement de ${amountLabel} vers ${bundleLabel} est en cours. Ne fermez pas cette fenêtre.`,
  successTitle: 'Portefeuille créé',
  successSubtitle: 'Votre allocation a été mise à jour.',
  v3QueuedTitle: 'Investissement enregistré',
  v3QueuedSubtitle:
    'Vos fonds ont été transférés vers le panier. Le rééquilibrage automatique se poursuit en arrière-plan — vous pouvez fermer cette page.',
  viewBasketCta: 'Voir mon panier',
  partialPreviewNote:
    'Certains actifs peuvent ne pas être entièrement disponibles — l’allocation pourrait être partielle.',
  rebalancePreparingSecureConfirmation: 'Préparation de la confirmation sécurisée…',
  rebalanceExecutingSwap: 'Exécution sécurisée du swap en cours…',
} as const

export const BUNDLE_TERMINAL_IMPOSSIBLE: TransactionTerminalFailureCopy = {
  title: 'Impossible de finaliser l’investissement',
  lines: ['Aucun portefeuille n’a été modifié.'],
}

/** Codes API bundle invest → message client (FR). */
export const BUNDLE_INVEST_ERROR_MESSAGES: Record<string, string> = {
  'bundle.funding.insufficient_self_trading':
    'Solde Mon Trading insuffisant pour ce montant. Créditez votre compte ou réduisez le montant investi.',
  'bundle.funding.invalid_amount': 'Montant d’investissement invalide.',
  bundle_funding_failed:
    'Impossible de transférer les fonds depuis Mon Trading. Vérifiez votre solde et réessayez.',
  v3_deposit_flow_resume_disabled:
    'Ce panier utilise le rééquilibrage automatique V3 — aucune reprise manuelle n’est nécessaire. Le traitement se poursuit en arrière-plan.',
  cash_rebalance_required:
    'La reprise invest est remplacée par le rééquilibrage portefeuille. Ouvrez le détail du panier et utilisez « Rééquilibrage ».',
  portfolio_rebalancing_required:
    'Utilisez le rééquilibrage portefeuille depuis le détail du panier (bouton Rééquilibrage).',
  portfolio_financial_operation_in_progress:
    'Une opération financière est déjà en cours sur ce portefeuille. Patientez quelques instants.',
}

export const BUNDLE_V3_REBALANCE_IN_PROGRESS_COPY: TransactionTerminalFailureCopy = {
  title: 'Rééquilibrage automatique en cours',
  lines: [
    'Ce panier utilise le nouveau flux d’investissement. Le rééquilibrage se poursuit en arrière-plan — aucune signature manuelle n’est requise.',
    'Si le cash leg reste non alloué après quelques minutes, utilisez « Réallouer le cash USDC ».',
  ],
}

const BUNDLE_FUNDING_ERROR_FALLBACK =
  'Impossible de transférer les fonds depuis Mon Trading. Vérifiez votre solde et réessayez.'

export function resolveBundleInvestErrorMessage(detail: string | null | undefined): string {
  const key = detail?.trim()
  if (!key) return 'Requête bundle impossible'
  if (BUNDLE_INVEST_ERROR_MESSAGES[key]) return BUNDLE_INVEST_ERROR_MESSAGES[key]!
  if (key.startsWith('bundle.funding.')) return BUNDLE_FUNDING_ERROR_FALLBACK
  return key
}

export const BUNDLE_TERMINAL_RECONCILIATION: TransactionTerminalFailureCopy = {
  title: 'Vérification nécessaire',
  lines: [
    'Une partie de votre allocation a été réalisée. Nous finalisons la réconciliation de votre portefeuille.',
  ],
}

/** R4.5-E.2-B — allocation partielle terminée dans la même session (pas recovery client). */
export const BUNDLE_TERMINAL_PARTIAL_ALLOCATION: TransactionTerminalFailureCopy = {
  title: 'Investissement partiellement réalisé',
  lines: [
    'Une partie de votre allocation a été réalisée. Le solde non investi reste disponible dans votre portefeuille.',
  ],
}

export const BUNDLE_BACKEND_LOCK_PENDING_LABEL = 'Verrou investissement encore actif côté serveur'

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

export const BUNDLE_WITHDRAW_REVIEW_UI = {
  title: 'Confirmation',
  confirmCta: 'Confirmer le retrait',
  modifierCta: 'Modifier',
  youWithdraw: 'Montant retiré',
  bundle: 'Panier',
  destination: 'Destination',
  destinationLabel: 'Mon Trading (USDC)',
  network: 'Réseau',
  networkLabel: 'Base',
  technicalDetailsTitle: 'Détails techniques',
} as const

export const BUNDLE_WITHDRAW_FLOW_UI = {
  setupTitle: () => 'Retirer',
  setupLead: (bundleTitle: string) =>
    `Retirez des fonds depuis ${bundleTitle}. Les USDC seront crédités sur Mon Trading.`,
  continueCta: 'Continuer',
  preparingSecureConfirmation: 'Préparation de la confirmation sécurisée…',
  processingTitle: 'Retrait en cours',
  processingLead: (amountLabel: string, bundleLabel: string) =>
    `Votre retrait de ${amountLabel} depuis ${bundleLabel} est en cours. Ne fermez pas cette fenêtre.`,
  successTitle: 'Retrait effectué',
  successSubtitle: 'Vos USDC sont en cours de synchronisation sur Mon Trading.',
  viewTradingCta: 'Voir Mon Trading',
  cashOnlyNote:
    'Le cash leg couvre le montant — transfert direct vers Mon Trading, sans vente d’actifs.',
  unwindNote:
    'Des positions du panier seront vendues avant le transfert des USDC vers Mon Trading.',
  releasePendingNote:
    'Les fonds apparaîtront sur Mon Trading une fois le transfert comptable confirmé.',
} as const

export const BUNDLE_WITHDRAW_TERMINAL_IMPOSSIBLE: TransactionTerminalFailureCopy = {
  title: 'Impossible de finaliser le retrait',
  lines: ['Aucun fonds n’a été transféré vers Mon Trading.'],
}

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
    BUNDLE_TERMINAL_PARTIAL_ALLOCATION.title,
    BUNDLE_TERMINAL_PARTIAL_ALLOCATION.lines[0]!,
  ]
}

export function assertNoBundlePrimaryJargon(text: string): void {
  if (BUNDLE_FORBIDDEN_PRIMARY_JARGON.test(text)) {
    throw new Error(`Bundle primary copy must not include jargon: ${text}`)
  }
}
