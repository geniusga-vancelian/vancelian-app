import type { PortalBundlePosition } from '@/lib/portal/cryptoWalletTypes'

export type BundleWithdrawDisplayPhase =
  | 'WITHDRAW_REQUESTED'
  | 'UNWINDING'
  | 'PARTIALLY_UNWOUND'
  | 'READY_TO_RELEASE'
  | 'RELEASED'
  | 'FAILED_PARTIAL'

export type BundleHoldingsSplit = {
  cashLeg: PortalBundlePosition | null
  cashLegQuantity: number
  spotAssets: PortalBundlePosition[]
  spotNotional: number
  totalWithdrawableEstimate: number
}

export type BundleWithdrawReleaseSnapshot = {
  released?: boolean
  amount?: number
  reason?: string
}

export type DirectTradingSnapshot = {
  usdcBalance: number
}

function positionNotional(position: PortalBundlePosition): number {
  if (position.marketValue != null && position.marketValue > 0) {
    return position.marketValue
  }
  if (position.asset.toUpperCase() === 'USDC' || position.asset.toUpperCase() === 'EURC') {
    return position.quantity
  }
  return position.costBasis
}

/** Répartit la vue bundle : cash leg USDC vs actifs alloués (spots). */
export function splitBundleHoldings(positions: PortalBundlePosition[] | undefined): BundleHoldingsSplit {
  const list = positions ?? []
  const cashCandidates = list.filter((p) => p.positionType === 'cash' && p.quantity > 0)
  const cashLeg = cashCandidates[0] ?? null
  const cashLegQuantity = cashLeg?.quantity ?? 0
  const spotAssets = list.filter((p) => p.positionType === 'spot' && p.quantity > 0)
  const spotNotional = spotAssets.reduce((sum, p) => sum + positionNotional(p), 0)
  const totalWithdrawableEstimate = cashLegQuantity + spotNotional
  return {
    cashLeg,
    cashLegQuantity,
    spotAssets,
    spotNotional,
    totalWithdrawableEstimate,
  }
}

/** Montant max estimé pour un retrait partiel (cash + valorisation spots). */
export function estimateMaxWithdrawAmount(positions: PortalBundlePosition[] | undefined): number {
  return splitBundleHoldings(positions).totalWithdrawableEstimate
}

export function mapWithdrawStatusToDisplayPhase(
  status: string | undefined,
  lockPhase?: string | null,
  release?: BundleWithdrawReleaseSnapshot | null,
): BundleWithdrawDisplayPhase {
  if (release?.released) return 'RELEASED'
  const phase = (lockPhase ?? '').trim().toUpperCase()
  if (
    phase === 'WITHDRAW_REQUESTED' ||
    phase === 'UNWINDING' ||
    phase === 'PARTIALLY_UNWOUND' ||
    phase === 'READY_TO_RELEASE' ||
    phase === 'RELEASED' ||
    phase === 'FAILED_PARTIAL'
  ) {
    return phase
  }
  const norm = (status ?? '').trim().toLowerCase()
  switch (norm) {
    case 'withdraw_requested':
      return 'WITHDRAW_REQUESTED'
    case 'unwinding':
    case 'pending_signature':
    case 'signature_requested':
    case 'submitted':
    case 'pending_confirmation':
      return 'UNWINDING'
    case 'partially_unwound':
    case 'partial':
      return 'PARTIALLY_UNWOUND'
    case 'ready_to_release':
    case 'finalizing':
      return 'READY_TO_RELEASE'
    case 'released':
    case 'completed':
      return 'RELEASED'
    case 'failed_partial':
    case 'failed':
      return 'FAILED_PARTIAL'
    default:
      return 'WITHDRAW_REQUESTED'
  }
}

/** Tant que le release comptable n'est pas confirmé, le self-trading ne doit pas créditer. */
export function isSelfTradingCreditPending(
  phase: BundleWithdrawDisplayPhase,
  release?: BundleWithdrawReleaseSnapshot | null,
): boolean {
  if (release?.released) return false
  return phase !== 'RELEASED'
}

/** Projection self-trading après release comptable (Privy inchangé). */
export function applyWithdrawReleaseToDirectSnapshot(
  direct: DirectTradingSnapshot,
  release: BundleWithdrawReleaseSnapshot,
): DirectTradingSnapshot {
  if (!release.released || !release.amount || release.amount <= 0) {
    return { ...direct }
  }
  return {
    usdcBalance: direct.usdcBalance + release.amount,
  }
}

/** Après vente confirmée : spot ↓, cash leg ↑ (sans toucher self-trading). */
export function applyConfirmedSellToBundleHoldings(
  holdings: BundleHoldingsSplit,
  args: { asset: string; quantitySold: number; entryReceived: number; entryAsset?: string },
): BundleHoldingsSplit {
  const entry = (args.entryAsset ?? 'USDC').toUpperCase()
  const assetU = args.asset.toUpperCase()
  const spotAssets = holdings.spotAssets.map((p) => {
    if (p.asset.toUpperCase() !== assetU) return p
    const nextQty = Math.max(0, p.quantity - args.quantitySold)
    const ratio = p.quantity > 0 ? nextQty / p.quantity : 0
    return {
      ...p,
      quantity: nextQty,
      costBasis: p.costBasis * ratio,
      marketValue: p.marketValue != null ? p.marketValue * ratio : p.marketValue,
    }
  }).filter((p) => p.quantity > 0)

  let cashLeg = holdings.cashLeg
  let cashLegQuantity = holdings.cashLegQuantity
  if (args.entryReceived > 0) {
    if (cashLeg && cashLeg.asset.toUpperCase() === entry) {
      cashLeg = {
        ...cashLeg,
        quantity: cashLeg.quantity + args.entryReceived,
        costBasis: cashLeg.costBasis + args.entryReceived,
      }
      cashLegQuantity = cashLeg.quantity
    } else {
      cashLeg = {
        asset: entry,
        quantity: (holdings.cashLegQuantity || 0) + args.entryReceived,
        costBasis: args.entryReceived,
        positionType: 'cash',
      }
      cashLegQuantity = cashLeg.quantity
    }
  }

  const spotNotional = spotAssets.reduce((sum, p) => sum + positionNotional(p), 0)
  return {
    cashLeg,
    cashLegQuantity,
    spotAssets,
    spotNotional,
    totalWithdrawableEstimate: cashLegQuantity + spotNotional,
  }
}
