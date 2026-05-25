import { formatPortalMoney, normalizeChartSeries, resolveSavingsPortfolioTotal, selectReferenceMoneyValue } from '@/lib/portal/dashboardFormat'
import { formatEarnApyFromBps, formatEarnTokenAmount } from '@/lib/portal/morphoVaultFormat'
import type { PortalSavingsPosition, PortalSavingsSummary, PortalSavingsVaultTransaction } from '@/lib/portal/portalSavingsTypes'

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
  currentBalanceUsd: number,
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

  if (rawHistory.length === 0 && currentBalanceUsd > 0) {
    rawHistory.push(currentBalanceUsd)
  } else if (currentBalanceUsd > 0) {
    rawHistory.push(currentBalanceUsd)
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
