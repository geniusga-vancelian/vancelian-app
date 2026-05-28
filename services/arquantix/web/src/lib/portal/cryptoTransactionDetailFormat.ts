import { formatPortalMoney } from '@/lib/portal/dashboardFormat'
import type { PortalCryptoWalletTransaction } from '@/lib/portal/cryptoWalletTypes'
import {
  isCryptoSwapTransaction,
  isLombardBorrowTransaction,
  isIncomingLeg,
  resolveSwapAssets,
  resolveSwapAmounts,
} from '@/lib/portal/cryptoTransactionHistoryFormat'

export type PortalTransactionDetailStatus = 'success' | 'pending' | 'failed'

export type PortalTransactionDetailStep = {
  name: string
  convert?: { from: string; to: string }
  amountLine?: string
  notes?: string[]
}

export type PortalTransactionDetailTimelineItem = {
  label: string
  time: string
  done: boolean
}

export type PortalTransactionDetailSummaryRow = {
  key: string
  value: string
}

export type PortalCryptoTransactionDetailViewModel = {
  id: string
  kindLabel: string
  status: PortalTransactionDetailStatus
  statusLabel: string
  statusTone: 'green' | 'warm' | 'error'
  title: string
  subtitle?: string
  amountLabel: string
  amountPositive: boolean
  dateLong: string
  stepperTitle: string
  steps: PortalTransactionDetailStep[]
  summary: PortalTransactionDetailSummaryRow[]
  timeline: PortalTransactionDetailTimelineItem[]
  counterparty?: { label: string; sub: string }
  flowDirection: 'in' | 'out'
  variant: 'flow' | 'swap' | 'borrow'
  fromAsset?: string
  toAsset?: string
}

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

function formatSignedAmountLabel(
  amount: string,
  asset: string,
  incoming: boolean,
  currency: string,
  fiatAmount?: string,
): string {
  const sign = incoming ? '+ ' : '− '
  const assetU = normalizeAsset(asset)
  if (amount.trim() && assetU) {
    return `${sign}${formatCryptoAmountDisplay(amount, assetU)}`
  }
  const fiatRaw = fiatAmount?.trim().replace(',', '.')
  if (fiatRaw && fiatRaw !== '0') {
    const fiatNum = Number(fiatRaw)
    if (!Number.isNaN(fiatNum) && fiatNum > 0) {
      return `${sign}${formatPortalMoney(fiatNum, currency)}`
    }
  }
  return '—'
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

function resolveTransactionStatus(tx: PortalCryptoWalletTransaction): {
  status: PortalTransactionDetailStatus
  label: string
  tone: 'green' | 'warm' | 'error'
} {
  const raw = tx.status?.trim().toLowerCase() ?? ''
  if (raw.includes('pend') || raw.includes('process')) {
    return { status: 'pending', label: 'En cours', tone: 'warm' }
  }
  if (
    raw.includes('fail') ||
    raw.includes('reject') ||
    raw.includes('revert') ||
    raw.includes('cancel')
  ) {
    return { status: 'failed', label: 'Échouée', tone: 'error' }
  }
  return { status: 'success', label: 'Réussie', tone: 'green' }
}

function resolveKindLabel(tx: PortalCryptoWalletTransaction): string {
  if (isLombardBorrowTransaction(tx)) return 'Emprunt'
  if (isCryptoSwapTransaction(tx)) return 'Échange'
  const side = tx.side?.trim().toLowerCase()
  if (side === 'buy' || side === 'deposit') return 'Versement'
  if (side === 'sell' || side === 'withdraw') return 'Retrait'
  if (side === 'swap') return 'Échange'
  return isIncomingLeg(tx) ? 'Versement' : 'Retrait'
}

function resolveStepperTitle(kindLabel: string): string {
  if (kindLabel === 'Échange') return "Étapes de l'échange"
  if (kindLabel === 'Versement') return 'Étapes du versement'
  if (kindLabel === 'Retrait') return 'Étapes du retrait'
  if (kindLabel === 'Emprunt') return "Étapes de l'emprunt"
  return "Étapes de l'opération"
}

function buildTimeline(
  tx: PortalCryptoWalletTransaction,
  status: PortalTransactionDetailStatus,
): PortalTransactionDetailTimelineItem[] {
  const time = formatTransactionTimeShort(tx.createdAt)
  const done = status === 'success'
  const pending = status === 'pending'

  const steps: PortalTransactionDetailTimelineItem[] = [
    { label: 'Ordre reçu', time, done: true },
  ]

  if (tx.txHash?.trim()) {
    steps.push({
      label: 'Confirmation on-chain',
      time: done ? time : pending ? 'En attente' : '—',
      done,
    })
  }

  steps.push({
    label: 'Fonds disponibles',
    time: done ? time : pending ? 'En cours' : '—',
    done,
  })

  return steps
}

function buildSummaryRows(
  tx: PortalCryptoWalletTransaction,
  currency: string,
): PortalTransactionDetailSummaryRow[] {
  const rows: PortalTransactionDetailSummaryRow[] = [
    { key: 'Référence', value: tx.id },
  ]

  if (tx.txHash?.trim()) {
    rows.push({ key: 'Hash blockchain', value: tx.txHash.trim() })
  }

  if (tx.asset?.trim()) {
    rows.push({ key: 'Actif', value: normalizeAsset(tx.asset) })
  }

  if (tx.amountCrypto?.trim()) {
    rows.push({
      key: 'Montant crypto',
      value: formatCryptoAmountDisplay(tx.amountCrypto, tx.asset),
    })
  }

  const fiatRaw = tx.amountFiat?.trim().replace(',', '.')
  if (fiatRaw && fiatRaw !== '0') {
    const fiatNum = Number(fiatRaw)
    if (!Number.isNaN(fiatNum) && fiatNum > 0) {
      rows.push({
        key: 'Contre-valeur',
        value: formatPortalMoney(fiatNum, tx.currency || currency),
      })
    }
  }

  if (tx.price?.trim() && tx.price !== '0') {
    rows.push({ key: "Prix d'exécution", value: tx.price.trim() })
  }

  if (tx.sourceSystem?.trim()) {
    rows.push({ key: 'Source', value: tx.sourceSystem.trim() })
  }

  rows.push({
    key: 'Statut',
    value: tx.status?.trim() || resolveTransactionStatus(tx).label,
  })

  return rows
}

function buildSteps(
  tx: PortalCryptoWalletTransaction,
  currency: string,
  incoming: boolean,
): PortalTransactionDetailStep[] {
  if (isLombardBorrowTransaction(tx)) {
    const collateral = normalizeAsset(tx.fromAsset) || 'COLLATERAL'
    const borrowAmount = tx.swapAmountTo?.trim() || tx.amountCrypto?.trim() || '0'
    const collateralAmount = tx.swapAmountFrom?.trim()
    return [
      {
        name: 'Garantie déposée',
        amountLine: collateralAmount
          ? `${formatCryptoAmountDisplay(collateralAmount, collateral)} bloqués en garantie.`
          : undefined,
        notes: ['La garantie reste verrouillée pendant la durée de l’emprunt.'],
      },
      {
        name: 'Crédit USDC versé',
        amountLine: `${formatCryptoAmountDisplay(borrowAmount, 'USDC')} crédités sur votre wallet.`,
        notes: ['Emprunt Lombard — taux variable selon le marché.'],
      },
    ]
  }

  if (isCryptoSwapTransaction(tx)) {
    const assets = resolveSwapAssets(tx)
    if (assets) {
      const amounts = resolveSwapAmounts(tx, assets)
      const from = amounts?.amountFrom
        ? formatCryptoAmountDisplay(amounts.amountFrom, assets.fromAsset)
        : '—'
      const to = amounts?.amountTo
        ? formatCryptoAmountDisplay(amounts.amountTo, assets.toAsset)
        : formatCryptoAmountDisplay(tx.amountCrypto ?? '0', assets.toAsset)

      return [
        {
          name: 'Conversion',
          convert: { from, to },
          notes: ['Conversion exécutée au prix de marché.'],
        },
        {
          name: 'Réception sur votre portefeuille',
          amountLine: `${to} crédités sur votre wallet.`,
          notes: ['Conservation institutionnelle (Fireblocks).'],
        },
      ]
    }
  }

  const asset = normalizeAsset(tx.asset)
  const amount = tx.amountCrypto?.trim()
  const amountLabel =
    amount && asset
      ? formatCryptoAmountDisplay(amount, asset)
      : tx.amountFiat?.trim()
        ? formatPortalMoney(Number(tx.amountFiat.replace(',', '.')), tx.currency || currency)
        : '—'

  if (incoming) {
    return [
      {
        name: 'Réception sur votre portefeuille',
        amountLine: `${amountLabel} crédités sur votre wallet crypto.`,
        notes: tx.subtitle?.trim() ? [tx.subtitle.trim()] : undefined,
      },
    ]
  }

  return [
    {
      name: 'Envoi depuis votre portefeuille',
      amountLine: `${amountLabel} débités de votre wallet crypto.`,
      notes: tx.subtitle?.trim() ? [tx.subtitle.trim()] : undefined,
    },
  ]
}

function buildCounterparty(
  tx: PortalCryptoWalletTransaction,
): { label: string; sub: string } | undefined {
  if (isLombardBorrowTransaction(tx)) {
    return { label: 'Lombard · Vancelian', sub: 'Crédit USDC contre garantie crypto' }
  }

  if (isCryptoSwapTransaction(tx)) {
    const assets = resolveSwapAssets(tx)
    if (assets) {
      return {
        label: 'Marché spot',
        sub: `${assets.fromAsset} → ${assets.toAsset}`,
      }
    }
  }

  if (tx.sourceSystem?.trim()) {
    return {
      label: tx.sourceSystem.trim(),
      sub: tx.subtitle?.trim() || 'Wallet Vancelian',
    }
  }

  if (tx.subtitle?.trim()) {
    return { label: 'Wallet Vancelian', sub: tx.subtitle.trim() }
  }

  return undefined
}

export function buildCryptoTransactionDetail(
  tx: PortalCryptoWalletTransaction,
  currency: string,
): PortalCryptoTransactionDetailViewModel {
  const incoming = isIncomingLeg(tx)
  const statusMeta = resolveTransactionStatus(tx)
  const kindLabel = resolveKindLabel(tx)
  const title = tx.title?.trim() || kindLabel
  const variant = isLombardBorrowTransaction(tx)
    ? 'borrow'
    : isCryptoSwapTransaction(tx)
      ? 'swap'
      : 'flow'

  let fromAsset: string | undefined
  let toAsset: string | undefined
  if (variant === 'swap' || variant === 'borrow') {
    const assets = resolveSwapAssets(tx)
    fromAsset = assets?.fromAsset ?? (normalizeAsset(tx.fromAsset) || undefined)
    toAsset = assets?.toAsset ?? (normalizeAsset(tx.toAsset) || undefined)
  }

  return {
    id: tx.id,
    kindLabel,
    status: statusMeta.status,
    statusLabel: statusMeta.label,
    statusTone: statusMeta.tone,
    title,
    subtitle: tx.subtitle?.trim() || undefined,
    amountLabel: formatSignedAmountLabel(
      tx.amountCrypto ?? '',
      tx.asset,
      incoming,
      currency,
      tx.amountFiat,
    ),
    amountPositive: incoming,
    dateLong: formatTransactionDateLong(tx.createdAt),
    stepperTitle: resolveStepperTitle(kindLabel),
    steps: buildSteps(tx, currency, incoming),
    summary: buildSummaryRows(tx, currency),
    timeline: buildTimeline(tx, statusMeta.status),
    counterparty: buildCounterparty(tx),
    flowDirection: incoming ? 'in' : 'out',
    variant,
    fromAsset,
    toAsset,
  }
}

export function findCryptoWalletTransactionById(
  transactions: PortalCryptoWalletTransaction[],
  txId: string,
): PortalCryptoWalletTransaction | undefined {
  const normalizedId = decodeURIComponent(txId.trim())
  return transactions.find((tx) => tx.id === normalizedId || tx.txHash === normalizedId)
}
