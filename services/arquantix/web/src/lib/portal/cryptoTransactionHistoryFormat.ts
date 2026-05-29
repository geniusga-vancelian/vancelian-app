import type { AppTxAmountTone } from '@/components/design-system/app/AppTxRow'
import { formatPortalMoney } from '@/lib/portal/dashboardFormat'
import type { PortalCryptoWalletTransaction } from '@/lib/portal/cryptoWalletTypes'
import { portalCryptoWalletTransactionRoute, portalCryptoWalletBundleTransactionRoute } from '@/lib/portal/portalRouting'

const FIAT_CURRENCIES = new Set(['EUR', 'USD', 'GBP', 'CHF'])
const SWAP_TITLE_RE = /(?:Échange|Exchange)\s+([A-Z0-9]+)\s*(?:→|->)\s*([A-Z0-9]+)/i

export type TransactionProjectionContext = 'self_trading' | 'bundle'

export type PortalCryptoTransactionHistoryItem = {
  id: string
  variant: 'flow' | 'swap' | 'borrow' | 'allocation'
  title: string
  subtitle?: string
  amount: string
  amountTone?: AppTxAmountTone
  meta?: string
  flowDirection?: 'in' | 'out'
  fromAsset?: string
  toAsset?: string
  href?: string
}

function normalizeAsset(value: string | undefined): string {
  return (value ?? '').trim().toUpperCase()
}

export function isIncomingLeg(tx: PortalCryptoWalletTransaction): boolean {
  const direction = tx.direction?.trim().toLowerCase()
  if (direction === 'credit' || direction === 'in') return true
  if (direction === 'debit' || direction === 'out') return false
  const side = tx.side?.trim().toLowerCase()
  return side === 'buy' || side === 'deposit'
}

export function parseSwapAssetsFromTitle(
  title: string | undefined,
): { fromAsset: string; toAsset: string } | null {
  const match = (title ?? '').trim().match(SWAP_TITLE_RE)
  if (!match?.[1] || !match?.[2]) return null
  return {
    fromAsset: normalizeAsset(match[1]),
    toAsset: normalizeAsset(match[2]),
  }
}

export function resolveSwapAssets(
  tx: PortalCryptoWalletTransaction,
): { fromAsset: string; toAsset: string } | null {
  const from = normalizeAsset(tx.fromAsset)
  const to = normalizeAsset(tx.toAsset)
  if (from && to && from !== to) {
    return { fromAsset: from, toAsset: to }
  }
  return parseSwapAssetsFromTitle(tx.title)
}

function formatCryptoAmountDisplay(amount: string): string {
  const raw = amount.trim().replace(',', '.')
  const parsed = Number(raw)
  if (Number.isNaN(parsed)) return amount.trim()
  const decimals = raw.includes('.') ? Math.min(8, raw.split('.')[1]?.length ?? 0) : 0
  return new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: Math.max(decimals, parsed < 1 ? 4 : 2),
  }).format(parsed)
}

function formatSignedCryptoAmount(amount: string, asset: string, sign: '+' | '−'): string {
  const assetU = normalizeAsset(asset)
  return `${sign}\u00a0${formatCryptoAmountDisplay(amount)}\u00a0${assetU}`
}

function formatTransactionDateLabel(tx: PortalCryptoWalletTransaction): string | undefined {
  if (!tx.createdAt) return undefined
  const date = new Date(tx.createdAt)
  if (Number.isNaN(date.getTime())) return undefined
  return new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' }).format(date)
}

function formatSwapExchangeTitle(fromAsset: string, toAsset: string): string {
  return `Échange · ${fromAsset} → ${toAsset}`
}

function formatTransactionMeta(tx: PortalCryptoWalletTransaction, currency: string): string | undefined {
  const parts: string[] = []
  const fiatRaw = tx.amountFiat?.trim().replace(',', '.')
  if (fiatRaw && fiatRaw !== '0' && fiatRaw !== '0.00') {
    const fiatNum = Number(fiatRaw)
    if (!Number.isNaN(fiatNum) && fiatNum > 0) {
      parts.push(`≈ ${formatPortalMoney(fiatNum, currency)}`)
    }
  }

  const dateLabel = formatTransactionDateLabel(tx)
  if (dateLabel) parts.push(dateLabel)

  return parts.length > 0 ? parts.join(' · ') : undefined
}

export function isLombardBorrowTransaction(tx: PortalCryptoWalletTransaction): boolean {
  const kind = tx.transactionKind?.trim().toLowerCase()
  if (kind === 'lombard_borrow') return true
  return tx.sourceSystem === 'lombard_v1'
}

export function isBundleInternalTransaction(tx: PortalCryptoWalletTransaction): boolean {
  const kind = tx.transactionKind?.trim().toLowerCase()
  if (kind === 'bundle_internal_swap') return true
  if (kind === 'bundle_allocation_aggregate' || kind === 'bundle_deallocation_aggregate') {
    return true
  }
  if (tx.portfolioScope?.trim().toLowerCase() === 'bundle' && tx.side?.trim().toLowerCase() === 'swap') {
    return true
  }
  const title = tx.title?.trim().toLowerCase() ?? ''
  if (
    (title.startsWith('allocation ·') || title.startsWith('allocation ')) &&
    kind !== 'bundle_allocation_aggregate'
  ) {
    return true
  }
  return false
}

export function isBundleAllocationAggregate(tx: PortalCryptoWalletTransaction): boolean {
  const kind = tx.transactionKind?.trim().toLowerCase()
  return kind === 'bundle_allocation_aggregate' || kind === 'bundle_deallocation_aggregate'
}

export function isCryptoSwapTransaction(
  tx: PortalCryptoWalletTransaction,
  context: TransactionProjectionContext = 'self_trading',
): boolean {
  if (isLombardBorrowTransaction(tx)) return false
  if (context === 'self_trading' && isBundleInternalTransaction(tx)) return false
  if (isBundleAllocationAggregate(tx)) return false

  const kind = tx.transactionKind?.trim().toLowerCase()
  if (kind === 'bundle_internal_swap') return false
  if (kind === 'crypto_swap') return true
  if (tx.side?.trim().toLowerCase() === 'swap') return true
  if (parseSwapAssetsFromTitle(tx.title)) return true

  const from = normalizeAsset(tx.fromAsset)
  const to = normalizeAsset(tx.toAsset)
  if (!from || !to || from === to) return false

  return !FIAT_CURRENCIES.has(from) && !FIAT_CURRENCIES.has(to)
}

export function resolveSwapAmounts(
  tx: PortalCryptoWalletTransaction,
  assets: { fromAsset: string; toAsset: string },
): { amountFrom: string; amountTo: string } | null {
  let amountFrom = tx.swapAmountFrom?.trim() ?? ''
  let amountTo = tx.swapAmountTo?.trim() ?? ''

  const currentAsset = normalizeAsset(tx.asset)
  const currentAmount = tx.amountCrypto?.trim() ?? ''

  if (!amountFrom && currentAsset === assets.fromAsset && currentAmount && !isIncomingLeg(tx)) {
    amountFrom = currentAmount
  }
  if (!amountTo && currentAsset === assets.toAsset && currentAmount && isIncomingLeg(tx)) {
    amountTo = currentAmount
  }
  if (!amountFrom && currentAsset === assets.fromAsset && currentAmount) {
    amountFrom = currentAmount
  }
  if (!amountTo && currentAsset === assets.toAsset && currentAmount) {
    amountTo = currentAmount
  }

  if (!amountFrom || !amountTo) return null
  return { amountFrom, amountTo }
}

function buildSwapGroupKey(
  tx: PortalCryptoWalletTransaction,
  assets: { fromAsset: string; toAsset: string },
): string {
  const hash = tx.txHash?.trim().toLowerCase()
  if (hash) return `hash:${hash}`
  return `swap:${assets.fromAsset}->${assets.toAsset}:${tx.title.trim()}:${tx.createdAt.slice(0, 19)}`
}

function mergeSwapGroup(group: PortalCryptoWalletTransaction[]): PortalCryptoWalletTransaction {
  const platform =
    group.find((tx) => tx.sourceSystem === 'lifi_swap' || tx.side?.trim().toLowerCase() === 'swap') ??
    group[0]!
  const assets = resolveSwapAssets(platform) ?? resolveSwapAssets(group[0]!)!
  let amountFrom = platform.swapAmountFrom?.trim() ?? ''
  let amountTo = platform.swapAmountTo?.trim() ?? ''

  for (const leg of group) {
    const asset = normalizeAsset(leg.asset)
    const amount = leg.amountCrypto?.trim() ?? ''
    if (leg.swapAmountFrom?.trim() && !amountFrom) amountFrom = leg.swapAmountFrom.trim()
    if (leg.swapAmountTo?.trim() && !amountTo) amountTo = leg.swapAmountTo.trim()
    if (!amount && !amountFrom && !amountTo) continue
    if (asset === assets.fromAsset && !amountFrom && !isIncomingLeg(leg)) {
      amountFrom = amount
    }
    if (asset === assets.toAsset && !amountTo && isIncomingLeg(leg)) {
      amountTo = amount
    }
  }

  return {
    ...platform,
    fromAsset: assets.fromAsset,
    toAsset: assets.toAsset,
    swapAmountFrom: amountFrom,
    swapAmountTo: amountTo,
    transactionKind: 'crypto_swap',
    side: 'swap',
    asset: assets.toAsset,
    amountCrypto: amountTo || amountFrom || platform.amountCrypto,
    direction: 'credit',
    title: platform.title?.trim() || `Échange ${assets.fromAsset} → ${assets.toAsset}`,
  }
}

/** Fusionne les jambes swap (Privy debit/credit) en une ligne avec from/to + montants. */
export function consolidateSwapTransactions(
  txs: PortalCryptoWalletTransaction[],
  context: TransactionProjectionContext = 'self_trading',
): PortalCryptoWalletTransaction[] {
  const passthrough: PortalCryptoWalletTransaction[] = []
  const swapGroups = new Map<string, PortalCryptoWalletTransaction[]>()

  for (const tx of txs) {
    if (!isCryptoSwapTransaction(tx, context)) {
      passthrough.push(tx)
      continue
    }

    const assets = resolveSwapAssets(tx)
    if (!assets) {
      passthrough.push(tx)
      continue
    }

    const enriched: PortalCryptoWalletTransaction = {
      ...tx,
      fromAsset: assets.fromAsset,
      toAsset: assets.toAsset,
    }
    const key = buildSwapGroupKey(enriched, assets)
    const group = swapGroups.get(key) ?? []
    group.push(enriched)
    swapGroups.set(key, group)
  }

  const consolidated = [...swapGroups.values()].map(mergeSwapGroup)
  return [...passthrough, ...consolidated]
}

function formatLombardBorrowMeta(collateralAmount: string | undefined, collateral: string): string | undefined {
  const amount = collateralAmount?.trim()
  const asset = normalizeAsset(collateral)
  if (!amount || !asset) return undefined
  return `Garantie · ${formatCryptoAmountDisplay(amount)} ${asset}`
}

function formatAllocationMeta(tx: PortalCryptoWalletTransaction): string | undefined {
  const parts: string[] = []
  const status = tx.status?.trim()
  if (status) parts.push(status)
  if (tx.legsCount != null) {
    parts.push(`${tx.successfulLegsCount ?? tx.legsCount}/${tx.legsCount} legs`)
  }
  const legs = tx.expandableLegs ?? []
  if (legs.length > 0) {
    const assets = [...new Set(legs.map((leg) => leg.toAsset).filter(Boolean))]
    if (assets.length > 0) parts.push(assets.join(', '))
  }
  const dateLabel = formatTransactionDateLabel(tx)
  if (dateLabel) parts.push(dateLabel)
  return parts.length > 0 ? parts.join(' · ') : undefined
}

export function mapCryptoTransactionToHistoryItem(
  tx: PortalCryptoWalletTransaction,
  currency: string,
  options?: { assetTicker?: string; projectionContext?: TransactionProjectionContext; bundlePortfolioId?: string },
): PortalCryptoTransactionHistoryItem {
  const projectionContext = options?.projectionContext ?? 'self_trading'
  const href = options?.bundlePortfolioId
    ? portalCryptoWalletBundleTransactionRoute(options.bundlePortfolioId, tx.id)
    : options?.assetTicker
      ? portalCryptoWalletTransactionRoute(options.assetTicker, tx.id)
      : undefined

  if (isBundleAllocationAggregate(tx)) {
    const asset = normalizeAsset(tx.asset) || 'USDC'
    const amount = tx.amountCrypto?.trim() || '0'
    return {
      id: tx.id,
      variant: 'allocation',
      title: tx.title?.trim() || 'Allocation · Bundle',
      subtitle: tx.subtitle?.trim() || undefined,
      amount: formatSignedCryptoAmount(amount, asset, '+'),
      amountTone: 'in',
      meta: formatAllocationMeta(tx),
      href,
    }
  }

  if (projectionContext === 'self_trading' && isBundleInternalTransaction(tx)) {
    return {
      id: tx.id,
      variant: 'flow',
      title: tx.title?.trim() || 'Opération bundle',
      subtitle: tx.subtitle?.trim(),
      amount: '—',
      href,
    }
  }

  if (isLombardBorrowTransaction(tx)) {
    const collateral = normalizeAsset(tx.fromAsset) || 'COLLATERAL'
    const borrowAmount =
      tx.swapAmountTo?.trim() || tx.amountCrypto?.trim() || '0'
    const collateralAmount = tx.swapAmountFrom?.trim()

    return {
      id: tx.id,
      variant: 'borrow',
      title: tx.title?.trim() || `Emprunt · ${collateral} → USDC`,
      subtitle: tx.subtitle?.trim() || formatTransactionDateLabel(tx),
      amount: formatSignedCryptoAmount(borrowAmount, 'USDC', '+'),
      amountTone: 'in',
      meta: formatLombardBorrowMeta(collateralAmount, collateral),
      fromAsset: collateral,
      toAsset: 'USDC',
      href,
    }
  }

  if (isCryptoSwapTransaction(tx, projectionContext)) {
    const assets = resolveSwapAssets(tx)
    if (assets) {
      const amounts = resolveSwapAmounts(tx, assets)
      const amountFrom = amounts?.amountFrom
      const amountTo =
        amounts?.amountTo ??
        (normalizeAsset(tx.asset) === assets.toAsset ? tx.amountCrypto?.trim() : undefined)

      return {
        id: tx.id,
        variant: 'swap',
        title: formatSwapExchangeTitle(assets.fromAsset, assets.toAsset),
        subtitle: formatTransactionDateLabel(tx),
        amount: amountTo
          ? formatSignedCryptoAmount(amountTo, assets.toAsset, '+')
          : formatSignedCryptoAmount(
              tx.amountCrypto ?? '0',
              normalizeAsset(tx.asset) || assets.toAsset,
              '+',
            ),
        amountTone: 'in',
        meta: amountFrom
          ? formatSignedCryptoAmount(amountFrom, assets.fromAsset, '−')
          : undefined,
        fromAsset: assets.fromAsset,
        toAsset: assets.toAsset,
        href,
      }
    }
  }

  const incoming = isIncomingLeg(tx)
  const amountTone: AppTxAmountTone = incoming ? 'in' : 'out'
  const sign = incoming ? '+' : '−'
  const cryptoAmount = tx.amountCrypto?.trim()
  const asset = normalizeAsset(tx.asset)
  const amount =
    cryptoAmount && asset
      ? formatSignedCryptoAmount(cryptoAmount, asset, sign)
      : tx.amountFiat?.trim() && tx.amountFiat !== '0'
        ? `${sign}\u00a0${formatPortalMoney(Number(tx.amountFiat.replace(',', '.')), tx.currency || currency)}`
        : '—'

  return {
    id: tx.id,
    variant: 'flow',
    title: tx.title?.trim() || (incoming ? 'Dépôt' : 'Retrait'),
    subtitle: tx.subtitle?.trim() || undefined,
    amount,
    amountTone,
    meta: formatTransactionMeta(tx, currency),
    flowDirection: incoming ? 'in' : 'out',
    href,
  }
}

const FRENCH_MONTHS_SHORT = [
  'Janv.',
  'Févr.',
  'Mars',
  'Avr.',
  'Mai',
  'Juin',
  'Juil.',
  'Août',
  'Sept.',
  'Oct.',
  'Nov.',
  'Déc.',
] as const

export function cryptoTransactionMonthKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

export function formatCryptoTransactionMonthChip(monthKey: string): string {
  const [year, month] = monthKey.split('-')
  const monthIndex = Number(month) - 1
  if (!year || monthIndex < 0 || monthIndex > 11) return monthKey
  return `${FRENCH_MONTHS_SHORT[monthIndex]} ${year}`
}

export function formatCryptoTransactionDayLabel(date: Date): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

export function listCryptoTransactionMonthKeys(txs: PortalCryptoWalletTransaction[]): string[] {
  const keys = new Set<string>()
  for (const tx of txs) {
    const date = new Date(tx.createdAt)
    if (Number.isNaN(date.getTime())) continue
    keys.add(cryptoTransactionMonthKey(date))
  }
  return [...keys].sort((a, b) => b.localeCompare(a))
}

export type PortalCryptoTransactionDaySection = {
  dayLabel: string
  items: PortalCryptoTransactionHistoryItem[]
}

/** Groupe les transactions par jour — layout All transactions (Flutter). */
export function groupCryptoTransactionsByDay(
  txs: PortalCryptoWalletTransaction[],
  currency: string,
  monthKey: string | null,
  assetTicker?: string,
  projectionContext: TransactionProjectionContext = 'self_trading',
): PortalCryptoTransactionDaySection[] {
  const filtered = monthKey
    ? txs.filter((tx) => {
        const date = new Date(tx.createdAt)
        return !Number.isNaN(date.getTime()) && cryptoTransactionMonthKey(date) === monthKey
      })
    : txs

  const sorted = [...filtered].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  )

  const byDay = new Map<string, PortalCryptoTransactionHistoryItem[]>()
  const dayLabels = new Map<string, string>()

  for (const tx of sorted) {
    const date = new Date(tx.createdAt)
    if (Number.isNaN(date.getTime())) continue
    const dayKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    if (!byDay.has(dayKey)) {
      byDay.set(dayKey, [])
      dayLabels.set(dayKey, formatCryptoTransactionDayLabel(date))
    }
    byDay.get(dayKey)!.push(
      mapCryptoTransactionToHistoryItem(tx, currency, { assetTicker, projectionContext }),
    )
  }

  return [...byDay.entries()]
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([dayKey, items]) => ({
      dayLabel: dayLabels.get(dayKey) ?? dayKey,
      items,
    }))
}
