/**
 * Processing UX abstraction — Phase 3B-R4.
 * Masque retry / revert / statuts internes ; le client voit uniquement
 * transaction en cours, réussie, ou impossible.
 */
import type { LombardBorrowRecap } from '@/lib/portal/lombard/lombardBorrowRecap'
import type { LombardExecutionPhase } from '@/lib/portal/lombard/lombardTypes'

export type LombardProcessingView = 'processing' | 'success' | 'terminal_failure'

export type LombardProcessingStep = {
  label: string
  defaultSub: (recap: LombardBorrowRecap) => string
}

export const LOMBARD_PROCESSING_STEPS: LombardProcessingStep[] = [
  {
    label: 'Autorisation de la garantie',
    defaultSub: (recap) =>
      `Vous autorisez l'utilisation de votre ${recap.collateral} comme garantie.`,
  },
  {
    label: 'Dépôt de la garantie',
    defaultSub: (recap) =>
      `${recap.guaranteeAmount} ${recap.collateral} sont déposés en garantie.`,
  },
  {
    label: "Ouverture de l'emprunt",
    defaultSub: (recap) =>
      `Emprunt de ${recap.borrowAmountLabel} USDC à ${recap.targetLtvPercent} % de niveau d'emprunt.`,
  },
  {
    label: 'Réception sur votre wallet',
    defaultSub: () => 'Les USDC arrivent sur votre wallet Vancelian.',
  },
]

export const LOMBARD_OPEN_LOAN_EXTENDED_SUBTEXTS = [
  (recap: LombardBorrowRecap) =>
    `Emprunt de ${recap.borrowAmountLabel} USDC à ${recap.targetLtvPercent} % de niveau d'emprunt.`,
  () => 'Vérification de votre garantie…',
  () => 'Connexion au protocole de prêt…',
  () => 'Finalisation de l’emprunt…',
  () => 'Validation des fonds…',
] as const

export type LombardTerminalFailureCopy = {
  title: string
  lines: string[]
}

export const LOMBARD_TERMINAL_FAILURE_COPY: LombardTerminalFailureCopy = {
  title: "Impossible d'ouvrir l'emprunt",
  lines: [
    "Aucun montant n'a été emprunté.",
    "Votre garantie n'a pas été déposée.",
  ],
}

/** Index stepper produit (0–3) ; 4 = terminé. */
export function lombardProcessingStepperIndex(phase: LombardExecutionPhase): number {
  switch (phase) {
    case 'preparing':
    case 'authorizing':
      return 0
    case 'locking':
      return 1
    case 'sending':
      return 2
    case 'confirming':
      return 3
    case 'confirmed':
      return 4
    default:
      return 0
  }
}

export function lombardProcessingStepperState(
  stepIndex: number,
  progressIndex: number,
): 'done' | 'current' | 'pending' {
  if (stepIndex < progressIndex) return 'done'
  if (stepIndex === progressIndex && progressIndex < 4) return 'current'
  return 'pending'
}

export function resolveOpenLoanStepSubtext(recap: LombardBorrowRecap, tick: number): string {
  const fn = LOMBARD_OPEN_LOAN_EXTENDED_SUBTEXTS[tick % LOMBARD_OPEN_LOAN_EXTENDED_SUBTEXTS.length]
  return fn(recap)
}

export function resolveProcessingStepSubtext(args: {
  stepIndex: number
  recap: LombardBorrowRecap
  openingSubtextTick: number
}): string {
  if (args.stepIndex === 2) {
    return resolveOpenLoanStepSubtext(args.recap, args.openingSubtextTick)
  }
  return LOMBARD_PROCESSING_STEPS[args.stepIndex]?.defaultSub(args.recap) ?? ''
}

export function isLombardOpeningPhase(phase: LombardExecutionPhase): boolean {
  return phase === 'locking' || phase === 'sending' || phase === 'confirming'
}
