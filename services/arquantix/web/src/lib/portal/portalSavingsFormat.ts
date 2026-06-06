import { formatPortalMoney, normalizeChartSeries, resolveSavingsPortfolioTotal, selectReferenceMoneyValue } from '@/lib/portal/dashboardFormat'
import { formatEarnApyFromBps, formatEarnTokenAmount } from '@/lib/portal/morphoVaultFormat'
import type { PortalSavingsPosition, PortalSavingsSummary, PortalSavingsVaultTransaction } from '@/lib/portal/portalSavingsTypes'

/** Taux indicatif USD → EUR pour valorisation croisée des stablecoins. */
export const SAVINGS_STABLECOIN_USD_TO_EUR = 0.92

const EUR_PEGGED_STABLECOIN_SYMBOLS = new Set(['EURC', 'LYEURC', 'VFEUR', 'LYEUR', 'EUR'])

export function isEurPeggedSavingsAsset(assetSymbol: string | null | undefined): boolean {
  return EUR_PEGGED_STABLECOIN_SYMBOLS.has(assetSymbol?.trim().toUpperCase() ?? '')
}

/** Valorisation native + EUR/USD selon l’actif ERC-4626 (1 USDC ≈ 1 $, 1 EURC ≈ 1 €). */
export function resolveStablecoinValuations(
  assetSymbol: string,
  humanAmount: number,
  usdToEur = SAVINGS_STABLECOIN_USD_TO_EUR,
): { nativeAmount: number; estimatedValueEur: number; estimatedValueUsd: number } {
  const amount = Number.isFinite(humanAmount) ? humanAmount : 0
  if (isEurPeggedSavingsAsset(assetSymbol)) {
    return {
      nativeAmount: amount,
      estimatedValueEur: amount,
      estimatedValueUsd: usdToEur > 0 ? amount / usdToEur : amount,
    }
  }
  return {
    nativeAmount: amount,
    estimatedValueUsd: amount,
    estimatedValueEur: amount * usdToEur,
  }
}

/** Code ISO affiché pour `formatPortalMoney` selon actif + devise de référence client. */
export function resolveSavingsDisplayCurrency(
  assetSymbol: string,
  referenceCurrency: string,
): string {
  const ref = referenceCurrency.trim().toUpperCase()
  if (isEurPeggedSavingsAsset(assetSymbol)) return 'EUR'
  if (ref === 'USD' || ref === 'USDT' || ref === 'USDC') return 'USD'
  return ref || 'EUR'
}

export function resolveSavingsCountLabel(summary: PortalSavingsSummary): string {
  const count = summary?.positions_count ?? summary?.positions?.length ?? 0
  if (count === 0) return 'Aucun vault pour le moment'
  return `${count} vault${count === 1 ? '' : 's'} DeFi`
}

export function resolveSavingsPositionValue(position: PortalSavingsPosition, currency: string): number {
  return selectReferenceMoneyValue(
    currency,
    position.estimatedValueEur,
    position.estimatedValueUsd ?? position.assetsUsd ?? undefined,
  )
}

export function formatSavingsPositionReferenceMoney(
  position: PortalSavingsPosition,
  referenceCurrency: string,
): string {
  const displayCurrency = resolveSavingsDisplayCurrency(position.assetSymbol, referenceCurrency)
  const value = resolveSavingsPositionValue(position, displayCurrency)
  return formatSavingsMoney(value, displayCurrency)
}

export function resolveSavingsVaultHeroSubtitle(args: {
  assetSymbol: string
  apyDisplay: string
  withdrawMode?: 'instant' | 'async_request' | 'blocked' | null
}): string {
  const liquidity =
    args.withdrawMode === 'async_request'
      ? 'retrait asynchrone'
      : args.withdrawMode === 'blocked'
        ? 'retrait bloqué'
        : 'liquidité instantanée'
  return `${args.assetSymbol} · ${args.apyDisplay} net · ${liquidity}`
}

export function resolveSavingsDailyYieldLabel(args: {
  position: PortalSavingsPosition
  apyBps: number | null | undefined
  referenceCurrency: string
}): string | null {
  const bps = args.apyBps
  if (bps == null || !Number.isFinite(bps) || bps <= 0) return null
  const balance = resolveSavingsPositionValue(args.position, args.referenceCurrency)
  if (balance <= 0) return null
  const daily = (balance * (bps / 10_000)) / 365
  const displayCurrency = resolveSavingsDisplayCurrency(
    args.position.assetSymbol,
    args.referenceCurrency,
  )
  return formatSavingsMoney(daily, displayCurrency)
}

export type PortalSavingsPositionStat = {
  key: string
  label: string
  value: string
  tone?: 'accent' | 'muted'
}

/** Lignes « Ma position » — devise de référence + contre-valorisation optionnelle. */
export function buildSavingsPositionStats(args: {
  position: PortalSavingsPosition
  referenceCurrency: string
  apyDisplay: string
}): PortalSavingsPositionStat[] {
  const { position, referenceCurrency, apyDisplay } = args
  const ref = referenceCurrency.trim().toUpperCase()
  const displayCurrency = resolveSavingsDisplayCurrency(position.assetSymbol, ref)
  const refValue = resolveSavingsPositionValue(position, displayCurrency)
  const refLabel = formatSavingsMoney(refValue, displayCurrency)
  const crossCurrency = displayCurrency === 'EUR' ? 'USD' : 'EUR'
  const crossValue = resolveSavingsPositionValue(position, crossCurrency)

  const rows: PortalSavingsPositionStat[] = [
    {
      key: 'total',
      label: 'Solde total',
      value: refLabel,
    },
    {
      key: 'vault',
      label: 'Montant dans le coffre',
      value: position.assetsInVaultDisplay,
    },
    {
      key: 'yield',
      label: 'Rendement cumulé',
      value: position.earnedYieldDisplay,
      tone: position.yieldSyncStatus === 'pending' ? 'muted' : 'accent',
    },
    {
      key: 'apy',
      label: 'Taux d’intérêt (APY)',
      value: apyDisplay,
    },
  ]

  if (displayCurrency === 'EUR') {
    rows.push({
      key: 'cross-usd',
      label: 'Valorisation USD',
      value: formatSavingsMoney(crossValue, 'USD'),
    })
  } else {
    rows.push({
      key: 'cross-eur',
      label: 'Valorisation EUR',
      value: formatSavingsMoney(crossValue, 'EUR'),
    })
  }

  return rows
}

export function formatSavingsMoney(amount: number | undefined, currency: string): string {
  if (amount == null || Number.isNaN(amount)) return '—'
  return formatPortalMoney(amount, currency)
}

export function resolveSavingsPositionSubtitle(position: PortalSavingsPosition): string {
  const apy =
    position.userApyBps != null && Number.isFinite(position.userApyBps)
      ? `${(position.userApyBps / 100).toFixed(2)}% APY`
      : null
  const parts = [position.assetsInVaultDisplay, position.provider.toUpperCase()]
  if (apy) parts.push(apy)
  return parts.join(' · ')
}

export function resolveSavingsHubTotalValue(summary: PortalSavingsSummary, currency: string): number {
  return resolveSavingsPortfolioTotal(summary, currency)
}

type LedgerTransactionInput = {
  id: string
  operation: string
  amountRaw: string
  assetSymbol: string
  assetDecimals: number
  status: string
  txHash: string | null
  walletAddress: string
  createdAt: Date
}

function formatVaultTransactionTitle(operation: string): string {
  switch (operation) {
    case 'deposit':
      return 'Dépôt'
    case 'withdraw':
      return 'Retrait'
    default:
      return operation
  }
}

function formatVaultTransactionStatus(status: string): string {
  switch (status) {
    case 'success':
      return 'Confirmé'
    case 'pending':
      return 'En cours'
    case 'reverted':
      return 'Annulé'
    case 'failed':
      return 'Échec'
    default:
      return status
  }
}

export function mapPortalSavingsVaultTransactions(
  rows: LedgerTransactionInput[],
  currentBalanceReference: number,
): { transactions: PortalSavingsVaultTransaction[]; historyPoints: number[] } {
  const chronological = [...rows]
    .filter((row) => row.status === 'success')
    .sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime())

  let balanceRaw = BigInt(0)
  const rawHistory: number[] = []
  for (const row of chronological) {
    const amount = BigInt(row.amountRaw || '0')
    if (row.operation === 'deposit') balanceRaw += amount
    if (row.operation === 'withdraw') balanceRaw -= amount
    const human = Number(formatEarnTokenAmount(balanceRaw.toString(), row.assetDecimals))
    if (Number.isFinite(human)) rawHistory.push(human)
  }

  if (rawHistory.length === 0 && currentBalanceReference > 0) {
    rawHistory.push(currentBalanceReference)
  } else if (currentBalanceReference > 0) {
    rawHistory.push(currentBalanceReference)
  }

  const historyPoints =
    rawHistory.length > 0
      ? normalizeChartSeries(rawHistory.map((performance_value) => ({ performance_value })))
      : []

  const transactions: PortalSavingsVaultTransaction[] = rows.map((row) => {
    const incoming = row.operation === 'deposit'
    const amountDisplay = `${formatEarnTokenAmount(row.amountRaw, row.assetDecimals)} ${row.assetSymbol}`
    const createdAt = row.createdAt.toISOString()
    const shortWallet = `${row.walletAddress.slice(0, 6)}…${row.walletAddress.slice(-4)}`

    return {
      id: row.id,
      operation: row.operation as PortalSavingsVaultTransaction['operation'],
      amountDisplay,
      assetSymbol: row.assetSymbol,
      status: row.status,
      txHash: row.txHash,
      walletAddress: row.walletAddress,
      createdAt,
      title: formatVaultTransactionTitle(row.operation),
      subtitle: `${formatVaultTransactionStatus(row.status)} · ${shortWallet}`,
      incoming,
    }
  })

  return { transactions, historyPoints }
}

export function formatSavingsTransactionAmount(tx: PortalSavingsVaultTransaction): string {
  const prefix = tx.incoming ? '+' : '−'
  return `${prefix}${tx.amountDisplay}`
}

export function formatSavingsApyLabel(apyBps: number | null | undefined): string {
  return formatEarnApyFromBps(apyBps ?? null)
}
