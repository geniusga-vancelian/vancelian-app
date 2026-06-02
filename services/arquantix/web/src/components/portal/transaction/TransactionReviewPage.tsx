'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { TransactionReviewPageProps } from '@/components/portal/transaction/types'

/**
 * Écran Review canon — non branché Lombard en R4.5-B (Review Lombard = phase ultérieure).
 */
export function TransactionReviewPage({
  title,
  children,
  primaryAction,
  onBack,
  onClose,
  backButtonLabel = 'Retour',
}: TransactionReviewPageProps) {
  return (
    <div className="inv-pane">
      <header className="inv-head">
        <h2 className="inv-head__title">{title}</h2>
        <div className="inv-head__actions">
          {onBack ? (
            <button type="button" className="inv-head__btn" onClick={onBack} aria-label="Retour">
              <KalaiIcon name="chevron-left" size={16} />
            </button>
          ) : null}
          {onClose ? (
            <button type="button" className="inv-head__btn" onClick={onClose} aria-label="Fermer">
              <KalaiIcon name="close" size={16} />
            </button>
          ) : null}
        </div>
      </header>

      <div className="inv-review-body">{children}</div>

      <div className="brw-foot inv-review-foot">
        {onBack ? (
          <button type="button" className="btn btn--ghost btn--lg" onClick={onBack}>
            {backButtonLabel}
          </button>
        ) : null}
        <button
          type="button"
          className="btn btn--primary btn--lg brw-foot__cta"
          disabled={primaryAction.disabled}
          onClick={primaryAction.onClick}
        >
          {primaryAction.label}
        </button>
      </div>
    </div>
  )
}
