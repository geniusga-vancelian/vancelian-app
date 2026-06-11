import type { ReactNode } from 'react'

/** Étape affichée dans TransactionStepList — jamais un statut backend brut. */
export type TransactionStep = {
  label: string
  subtext: string
}

/** État visuel d'une étape du stepper (processing). */
export type TransactionStepMarkerState = 'pending' | 'loading' | 'done' | 'failed'

/** @deprecated Préférer TransactionStepMarkerState — conservé pour l'index monotone legacy. */
export type TransactionStepperMarkerState = 'done' | 'current' | 'pending'

/** Machine UI — distincte des statuts intent / OVT backend. */
export type TransactionStatus =
  | 'idle'
  | 'reviewing'
  | 'signing'
  | 'processing'
  | 'success'
  | 'impossible'
  | 'reconciliation_required'

export type TransactionTerminalFailureCopy = {
  title: string
  lines: string[]
}

export type TransactionProcessingPageProps = {
  title: string
  lead: ReactNode
  steps: TransactionStep[]
  progressIndex: number
  /** Index à partir duquel toutes les étapes sont terminées (ex. Lombard = 4). */
  completedProgressIndex: number
  /** États explicites par step — prioritaire sur progressIndex quand fourni. */
  stepStates?: TransactionStepMarkerState[]
  onClose: () => void
  cardClassName?: string
}

export type TransactionResultSuccessStep = {
  name: string
  body: ReactNode
}

export type TransactionResultSummaryRow = {
  k: string
  v: string
}

export type TransactionResultSuccessProps = {
  variant: 'success'
  /** `compact` — hero + CTA (swap) ; `full` — stepper recap (Lombard). */
  layout?: 'full' | 'compact'
  title: string
  lead: ReactNode
  /** Ligne secondaire sous le lead (layout compact). */
  subtitle?: ReactNode
  steps: TransactionResultSuccessStep[]
  /** Titre de la section étapes (layout full). */
  stepsTitle?: string
  /** Titre du récapitulatif (layout full). */
  summaryTitle?: string
  summary: TransactionResultSummaryRow[]
  note?: ReactNode
  primaryAction: {
    label: string
    onClick: () => void
    icon?: ReactNode
  }
  onClose?: () => void
  cardClassName?: string
}

export type TransactionResultImpossibleProps = {
  variant: 'impossible'
  copy: TransactionTerminalFailureCopy
  onRetry?: () => void
  onClose: () => void
  retryDisabled?: boolean
  closeLabel?: string
  retryLabel?: string
}

export type TransactionResultReconciliationProps = {
  variant: 'reconciliation_required'
  copy: TransactionTerminalFailureCopy
  onClose: () => void
  closeLabel?: string
  primaryAction?: {
    label: string
    onClick: () => void
  }
  technicalDetails?: TransactionTechnicalDetailsRow[]
  technicalDetailsTitle?: string
}

export type TransactionResultPageProps =
  | TransactionResultSuccessProps
  | TransactionResultImpossibleProps
  | TransactionResultReconciliationProps

export type TransactionTechnicalDetailsRow = {
  label: string
  value: string
}

export type TransactionReviewPageProps = {
  title: string
  children: ReactNode
  primaryAction: {
    label: string
    onClick: () => void
    disabled?: boolean
  }
  onBack?: () => void
  onClose?: () => void
  backButtonLabel?: string
  /** Handoff InvestConfirm — flèche avant le titre, pied « Modifier » secondaire. */
  layout?: 'default' | 'confirm'
}
