import {
  buildCryptoTransactionDetail,
  type PortalCryptoTransactionDetailViewModel,
  type PortalTransactionDetailStep,
  type PortalTransactionDetailSummaryRow,
} from '@/lib/portal/cryptoTransactionDetailFormat'
import {
  isBundleAllocationAggregate,
  isBundleRebalanceAggregate,
} from '@/lib/portal/cryptoTransactionHistoryFormat'
import type {
  PortalBundleAllocationLeg,
  PortalCryptoWalletTransaction,
} from '@/lib/portal/cryptoWalletTypes'

function normalizeAsset(value: string | undefined): string {
  return (value ?? '').trim().toUpperCase()
}

function formatCryptoAmountDisplay(amount: string, asset: string): string {
  const raw = amount.trim().replace(',', '.')
  const parsed = Number(raw)
  const assetU = normalizeAsset(asset)
  if (Number.isNaN(parsed)) return `${amount.trim()} ${assetU}`
  const decimals = raw.includes('.') ? Math.min(8, raw.split('.')[1]?.length ?? 0) : 0
  const formatted = new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: Math.max(decimals, parsed < 1 ? 4 : 2),
  }).format(parsed)
  return `${formatted}\u00a0${assetU}`
}

function formatTransactionDateLong(createdAt: string): string {
  const date = new Date(createdAt)
  if (Number.isNaN(date.getTime())) return '—'
  const datePart = new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
  const timePart = new Intl.DateTimeFormat('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
    .format(date)
    .replace(':', ' h ')
  return `${datePart} · ${timePart}`
}

function formatTransactionTimeShort(createdAt: string): string {
  const date = new Date(createdAt)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
    .format(date)
    .replace(':', ' h ')
}

function resolveAllocationStatus(tx: PortalCryptoWalletTransaction): {
  status: 'success' | 'pending' | 'failed'
  label: string
  tone: 'green' | 'warm' | 'error'
} {
  const raw = tx.status?.trim().toLowerCase() ?? ''
  if (raw === 'partial') {
    return { status: 'pending', label: 'Partielle', tone: 'warm' }
  }
  if (raw.includes('progress') || raw.includes('pend')) {
    return { status: 'pending', label: 'En cours', tone: 'warm' }
  }
  if (raw.includes('fail') || raw === 'failed') {
    return { status: 'failed', label: 'Échouée', tone: 'error' }
  }
  return { status: 'success', label: 'Terminée', tone: 'green' }
}

function legStatusLabel(status: string | undefined): string {
  const raw = status?.trim().toLowerCase() ?? ''
  if (raw.includes('fail')) return 'Échouée'
  if (raw.includes('pend') || raw.includes('progress')) return 'En cours'
  return 'Confirmée'
}

function buildAllocationLegStep(leg: PortalBundleAllocationLeg, index: number): PortalTransactionDetailStep {
  const fromAsset = normalizeAsset(leg.fromAsset)
  const toAsset = normalizeAsset(leg.toAsset)
  const amountIn = leg.amountIn?.trim()
  const amountOut = leg.amountOut?.trim()
  const notes: string[] = [`Statut · ${legStatusLabel(leg.status)}`]
  if (leg.txHash?.trim()) {
    notes.push(`Hash · ${leg.txHash.trim()}`)
  }

  return {
    name: `Exécution ${index + 1} · ${fromAsset} → ${toAsset}`,
    convert:
      amountIn && amountOut
        ? {
            from: formatCryptoAmountDisplay(amountIn, fromAsset),
            to: formatCryptoAmountDisplay(amountOut, toAsset),
          }
        : undefined,
    amountLine: amountIn
      ? `${formatCryptoAmountDisplay(amountIn, fromAsset)} convertis via Li.FI.`
      : undefined,
    notes,
  }
}

function buildAllocationSummaryRows(tx: PortalCryptoWalletTransaction): PortalTransactionDetailSummaryRow[] {
  const rows: PortalTransactionDetailSummaryRow[] = [
    { key: 'Référence', value: tx.id },
  ]

  if (tx.bundleBatchId?.trim()) {
    rows.push({ key: 'Batch', value: tx.bundleBatchId.trim() })
  }

  if (tx.legsCount != null) {
    const ok = tx.successfulLegsCount ?? tx.legsCount
    rows.push({ key: 'Jambes exécutées', value: `${ok}/${tx.legsCount}` })
  }

  if (tx.amountCrypto?.trim() && tx.asset?.trim()) {
    rows.push({
      key: 'Montant alloué',
      value: formatCryptoAmountDisplay(tx.amountCrypto, tx.asset),
    })
  }

  rows.push({
    key: 'Statut',
    value: resolveAllocationStatus(tx).label,
  })

  rows.push({ key: 'Exécution', value: 'Li.FI · swaps on-chain' })

  return rows
}

function buildAllocationAggregateDetail(
  tx: PortalCryptoWalletTransaction,
): PortalCryptoTransactionDetailViewModel {
  const statusMeta = resolveAllocationStatus(tx)
  const asset = normalizeAsset(tx.asset) || 'USDC'
  const amount = tx.amountCrypto?.trim() || '0'
  const legs = tx.expandableLegs ?? []
  const legsLabel =
    tx.legsCount != null
      ? `${tx.successfulLegsCount ?? tx.legsCount}/${tx.legsCount} legs`
      : undefined

  return {
    id: tx.id,
    kindLabel: 'Allocation',
    status: statusMeta.status,
    statusLabel: statusMeta.label,
    statusTone: statusMeta.tone,
    title: tx.title?.trim() || 'Allocation · Bundle',
    subtitle: tx.subtitle?.trim() || legsLabel,
    amountLabel: `${formatCryptoAmountDisplay(amount, asset)} alloués`,
    amountPositive: true,
    dateLong: formatTransactionDateLong(tx.createdAt),
    stepperTitle: 'Exécutions Li.FI',
    steps: legs.length > 0 ? legs.map(buildAllocationLegStep) : [],
    summary: buildAllocationSummaryRows(tx),
    timeline: [
      { label: 'Ordre reçu', time: formatTransactionTimeShort(tx.createdAt), done: true },
      {
        label: 'Swaps Li.FI',
        time: statusMeta.status === 'success' ? formatTransactionTimeShort(tx.createdAt) : 'En cours',
        done: statusMeta.status === 'success',
      },
      {
        label: 'Allocation terminée',
        time: statusMeta.status === 'success' ? formatTransactionTimeShort(tx.createdAt) : '—',
        done: statusMeta.status === 'success',
      },
    ],
    counterparty: {
      label: 'Li.FI',
      sub: legs.length > 0 ? `${legs.length} exécutions on-chain` : 'Agrégat bundle',
    },
    flowDirection: 'in',
    variant: 'allocation',
  }
}

function buildRebalanceAggregateDetail(
  tx: PortalCryptoWalletTransaction,
): PortalCryptoTransactionDetailViewModel {
  const statusMeta = resolveAllocationStatus(tx)
  const legs = tx.expandableLegs ?? []
  const legsLabel =
    tx.legsCount != null
      ? `${tx.successfulLegsCount ?? tx.legsCount}/${tx.legsCount} legs`
      : undefined

  return {
    id: tx.id,
    kindLabel: 'Rééquilibrage',
    status: statusMeta.status,
    statusLabel: statusMeta.label,
    statusTone: statusMeta.tone,
    title: tx.title?.trim() || 'Rééquilibrage · Bundle',
    subtitle: tx.subtitle?.trim() || legsLabel,
    amountLabel: legs.length > 0 ? `${legs.length} exécutions Li.FI` : 'Rééquilibrage bundle',
    amountPositive: true,
    dateLong: formatTransactionDateLong(tx.createdAt),
    stepperTitle: 'Exécutions Li.FI',
    steps: legs.length > 0 ? legs.map(buildAllocationLegStep) : [],
    summary: buildAllocationSummaryRows(tx).filter((row) => row.key !== 'Montant alloué'),
    timeline: [
      { label: 'Plan calculé', time: formatTransactionTimeShort(tx.createdAt), done: true },
      {
        label: 'Swaps Li.FI',
        time: statusMeta.status === 'success' ? formatTransactionTimeShort(tx.createdAt) : 'En cours',
        done: statusMeta.status === 'success',
      },
      {
        label: 'Rééquilibrage terminé',
        time: statusMeta.status === 'success' ? formatTransactionTimeShort(tx.createdAt) : '—',
        done: statusMeta.status === 'success',
      },
    ],
    counterparty: {
      label: 'Li.FI',
      sub: legs.length > 0 ? `${legs.length} exécutions on-chain` : 'Agrégat bundle',
    },
    flowDirection: 'in',
    variant: 'allocation',
  }
}

/** Détail transaction bundle — dépôt, retrait, allocation agrégée. */
export function buildBundleTransactionDetail(
  tx: PortalCryptoWalletTransaction,
  currency: string,
): PortalCryptoTransactionDetailViewModel {
  if (isBundleRebalanceAggregate(tx)) {
    return buildRebalanceAggregateDetail(tx)
  }
  if (isBundleAllocationAggregate(tx)) {
    return buildAllocationAggregateDetail(tx)
  }
  return buildCryptoTransactionDetail(tx, currency)
}

export function findBundleTransactionById(
  transactions: PortalCryptoWalletTransaction[],
  txId: string,
): PortalCryptoWalletTransaction | undefined {
  const normalizedId = decodeURIComponent(txId.trim())
  return transactions.find(
    (tx) =>
      tx.id === normalizedId ||
      tx.txHash === normalizedId ||
      tx.bundleBatchId === normalizedId,
  )
}
