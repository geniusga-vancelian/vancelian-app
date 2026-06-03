/**
 * Primary user-facing copy for the swap flow (EN) — R4.5-C.
 * Technical details may expose route labels from the API; main UI must stay jargon-free.
 */
export const SWAP_FORBIDDEN_PRIMARY_JARGON =
  /revert|retryable_failed|group_key|logical_borrow_id|idempotency|lifi|li\.fi|token approval|tx reverted|0x[a-f0-9]{8,}/i

export const SWAP_REVIEW_UI = {
  title: 'Exchange summary',
  confirmCta: 'Confirm exchange',
  youPay: 'You pay',
  youReceive: 'You receive',
  amountPaidAria: 'Amount to pay',
  amountReceiveAria: 'Estimated receive amount',
  exchangeRate: 'Exchange rate',
  minimumReceive: 'Minimum receive',
  vancelianFees: 'Vancelian fees',
  vancelianFeesWaived: 'Waived',
  networkFees: 'Network fees',
  network: 'Network',
  technicalDetailsTitle: 'Technical details',
  backButton: 'Back',
} as const

export const SWAP_FLOW_UI = {
  processingTitle: 'Transaction in progress',
  processingLead: (payLabel: string, fromAsset: string, toAsset: string) =>
    `Your exchange of ${payLabel} ${fromAsset} to ${toAsset} is being processed. Do not close this window.`,
  successTitle: 'Exchange completed',
  successSubtitle: (payLabel: string, fromAsset: string) => `for ${payLabel} ${fromAsset}`,
  viewWalletCta: (toAsset: string) => `View ${toAsset} wallet`,
  backToWallet: 'Back to wallet',
  preparingSecureConfirmation: 'Preparing secure confirmation…',
  quoteExpiredLine:
    'Your quote has expired. Go back to the amount step and request a new estimate.',
} as const

export const SWAP_RESULT_IMPOSSIBLE_ACTIONS = {
  close: 'Close',
  retry: 'Try again',
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
