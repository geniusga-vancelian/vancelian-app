/** Scènes UX Bundle invest / retrait (R4.5-E) — page dédiée, pas modale. */
export type PortalBundleFlowScene = 'setup' | 'review' | 'processing' | 'result' | 'blocked'

export type PortalBundleWithdrawResultVariant = 'success' | 'impossible'

export type PortalBundleInvestResultVariant =
  | 'success'
  | 'completed_partial_allocation'
  | 'impossible'
  | 'reconciliation_required'
  | 'v3_deposit_queued'
