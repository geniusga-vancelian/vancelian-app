import { isLombardV1Enabled, LOMBARD_INTEGRATION_MODE } from '@/lib/portal/lombard/lombardConfig'
import { rawToLombardHumanAmount } from '@/lib/portal/lombard/lombardFormat'
import type { PortalCryptoWalletTransaction } from '@/lib/portal/cryptoWalletTypes'
import { prisma } from '@/lib/prisma'

const USDC_DECIMALS = 6

function readMetadata(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

function readString(meta: Record<string, unknown>, key: string): string {
  const raw = meta[key]
  return typeof raw === 'string' ? raw.trim() : ''
}

function formatLombardBorrowTitle(collateral: string): string {
  return `Emprunt · ${collateral} → USDC`
}

function mapLedgerRowToBorrowTransaction(row: {
  id: string
  idempotencyKey: string
  amountRaw: string
  txHash: string | null
  createdAt: Date
  metadataJson: unknown
}): PortalCryptoWalletTransaction | null {
  const meta = readMetadata(row.metadataJson)
  if (readString(meta, 'lombard_operation') !== 'open_loan') return null

  const collateral = readString(meta, 'collateral').toUpperCase() || 'COLLATERAL'
  const borrowAmount =
    readString(meta, 'borrow_amount') ||
    rawToLombardHumanAmount(BigInt(String(row.amountRaw || '0')), USDC_DECIMALS, 6)
  const guaranteeAmount = readString(meta, 'guarantee_amount')

  if (!borrowAmount || borrowAmount === '0') return null

  const groupKey = row.idempotencyKey.trim() || readString(meta, 'group_key')

  return {
    id: `lombard-borrow-${groupKey || row.id}`,
    side: 'deposit',
    asset: 'USDC',
    amountCrypto: borrowAmount,
    amountFiat: '',
    price: '',
    currency: 'EUR',
    status: 'success',
    createdAt: row.createdAt.toISOString(),
    title: formatLombardBorrowTitle(collateral),
    subtitle: 'Morpho · Base',
    direction: 'credit',
    transactionKind: 'lombard_borrow',
    sourceSystem: 'lombard_v1',
    fromAsset: collateral,
    toAsset: 'USDC',
    swapAmountFrom: guaranteeAmount || undefined,
    swapAmountTo: borrowAmount,
    txHash: row.txHash?.trim() || undefined,
  }
}

/** Emprunts Lombard USDC confirmés — visibles dans l'historique wallet (sans approve / supply). */
export async function fetchLombardBorrowWalletTransactions(args: {
  personId: string
  walletAddress: string
  asset: string
}): Promise<{ transactions: PortalCryptoWalletTransaction[]; hiddenPrivyKeys: Set<string> }> {
  if (!isLombardV1Enabled()) return { transactions: [], hiddenPrivyKeys: new Set() }
  const asset = args.asset.trim().toUpperCase()
  if (asset !== 'USDC') return { transactions: [], hiddenPrivyKeys: new Set() }

  const wallet = args.walletAddress.trim().toLowerCase()
  if (!wallet) return { transactions: [], hiddenPrivyKeys: new Set() }

  const rows = await prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      walletAddress: wallet,
      integrationMode: LOMBARD_INTEGRATION_MODE,
      operation: 'deposit',
      status: 'success',
    },
    orderBy: { createdAt: 'desc' },
    take: 50,
  })

  const seen = new Set<string>()
  const out: PortalCryptoWalletTransaction[] = []
  const hiddenPrivyKeys = new Set<string>()

  for (const row of rows) {
    const meta = readMetadata(row.metadataJson)
    const privyTxHash = readString(meta, 'mock_usdc_privy_tx_hash').toLowerCase()
    if (privyTxHash) hiddenPrivyKeys.add(`hash:${privyTxHash}`)
    const privyDepositId = readString(meta, 'mock_usdc_privy_deposit_id')
    if (privyDepositId) hiddenPrivyKeys.add(`id:${privyDepositId}`)

    const tx = mapLedgerRowToBorrowTransaction(row)
    if (!tx || seen.has(tx.id)) continue
    seen.add(tx.id)
    out.push(tx)
  }

  for (const key of collectLombardHiddenPrivyDepositKeys(out)) {
    hiddenPrivyKeys.add(key)
  }

  return { transactions: out, hiddenPrivyKeys }
}

export function collectLombardHiddenPrivyDepositKeys(
  lombardTxs: PortalCryptoWalletTransaction[],
): Set<string> {
  const keys = new Set<string>()
  for (const tx of lombardTxs) {
    const hash = tx.txHash?.trim().toLowerCase()
    if (hash) keys.add(`hash:${hash}`)
    const amount = tx.amountCrypto?.trim()
    if (amount) keys.add(`amount:${amount}`)
  }
  return keys
}

/** Masque les crédits Privy génériques déjà représentés par une ligne emprunt Lombard. */
export function shouldHidePrivyDepositForLombardBorrow(
  tx: PortalCryptoWalletTransaction,
  hiddenKeys: Set<string>,
): boolean {
  if (tx.transactionKind?.trim().toLowerCase() === 'lombard_borrow') return false
  if (tx.sourceSystem === 'lombard_v1') return false

  const kind = tx.transactionKind?.trim().toLowerCase()
  const title = tx.title?.trim().toLowerCase() ?? ''
  const isGenericPrivyDeposit =
    kind === 'privy_deposit_in' ||
    (tx.sourceSystem === 'privy' && title.startsWith('dépôt') && !title.includes('→'))
  if (!isGenericPrivyDeposit) return false

  const hash = tx.txHash?.trim().toLowerCase()
  if (hash && hiddenKeys.has(`hash:${hash}`)) return true

  const id = tx.id?.trim()
  if (id && hiddenKeys.has(`id:${id}`)) return true

  const amount = tx.amountCrypto?.trim()
  if (amount && hiddenKeys.has(`amount:${amount}`)) return true

  return false
}
