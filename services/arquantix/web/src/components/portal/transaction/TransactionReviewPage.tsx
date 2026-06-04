'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { TransactionReviewPageProps } from '@/components/portal/transaction/types'

/** Écran Review canon — swap, vault, bundle, Lombard (O4). */
export function TransactionReviewPage({
  title,
  children,
  primaryAction,
  onBack,
  onClose,
  backButtonLabel = 'Retour',
  layout = 'default',
}: TransactionReviewPageProps) {
  const isConfirm = layout === 'confirm'

  return (
    <div className={`inv-pane${isConfirm ? ' inv-confirm' : ''}`}>
      <header className={`inv-head${isConfirm ? ' inv-head--confirm' : ''}`}>
        {isConfirm ? (
          <>
            {onBack ? (
              <button
                type="button"
                className="inv-head__btn inv-confirm__back"
                onClick={onBack}
                aria-label="Retour"
              >
                <KalaiIcon name="arrow-right" size={16} style={{ transform: 'rotate(180deg)' }} />
              </button>
            ) : (
              <span className="inv-confirm__head-spacer" aria-hidden />
            )}
            <h2 className="inv-head__title">{title}</h2>
            {onClose ? (
              <button type="button" className="inv-head__btn inv-confirm__close" onClick={onClose} aria-label="Fermer">
                <KalaiIcon name="close" size={16} />
              </button>
            ) : (
              <span className="inv-confirm__head-spacer" aria-hidden />
            )}
          </>
        ) : (
          <>
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
          </>
        )}
      </header>

      <div className="inv-review-body">{children}</div>

      <div className={`brw-foot inv-review-foot${isConfirm ? ' inv-confirm__actions' : ''}`}>
        {onBack ? (
          <button
            type="button"
            className={`btn btn--lg${isConfirm ? ' btn--secondary' : ' btn--ghost'}`}
            onClick={onBack}
          >
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
