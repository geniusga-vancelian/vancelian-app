import type { TransactionTerminalFailureCopy } from '@/components/portal/transaction/types'

/** Erreur API prepare Lombard — avant toute signature / tx on-chain. */
export class LombardPrepareBlockedError extends Error {
  readonly code: string
  readonly httpStatus: number

  constructor(code: string, message: string, httpStatus = 400) {
    super(message)
    this.name = 'LombardPrepareBlockedError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

/** Codes où le devis UI aurait dû bloquer avant prepare (régression quote ↔ prepare). */
export const LOMBARD_QUOTE_PREPARE_DRIFT_CODES = new Set([
  'lombard.borrow_exceeds_capacity',
  'lombard.insufficient_guarantee_balance',
  'lombard.balance_changed',
  'lombard.ltv_cap_exceeded',
  'lombard.insufficient_liquidity',
])

export function isLombardQuotePrepareDriftCode(code: string): boolean {
  return LOMBARD_QUOTE_PREPARE_DRIFT_CODES.has(code)
}

export function buildPrepareBlockedTerminalCopy(args: {
  message: string
  autoRetryAttempted?: boolean
}): TransactionTerminalFailureCopy {
  return {
    title: "Impossible d'ouvrir l'emprunt",
    lines: [
      args.message,
      'Aucune transaction n\'a été envoyée — votre garantie n\'a pas été déposée.',
      args.autoRetryAttempted
        ? 'Une nouvelle tentative automatique a déjà été effectuée. Voulez-vous recommencer ?'
        : 'Vérifiez le montant ou réessayez dans quelques instants.',
    ],
  }
}

export function resolvePrepareBlockedDriftReason(args: {
  errorCode: string
  portalWalletCollateralBalance?: string | null
}): 'prepare_missing_portal_balance' | 'quote_prepare_capacity_mismatch' {
  const portalSent = Boolean(args.portalWalletCollateralBalance?.trim())
  if (
    !portalSent &&
    (args.errorCode === 'lombard.borrow_exceeds_capacity' ||
      args.errorCode === 'lombard.insufficient_guarantee_balance')
  ) {
    return 'prepare_missing_portal_balance'
  }
  return 'quote_prepare_capacity_mismatch'
}
