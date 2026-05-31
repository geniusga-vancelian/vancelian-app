import { BASE_CHAIN_ID, invParseAmount } from '@/lib/portal/portalInvestFlowFormat'

export class VaultDepositLimitError extends Error {
  readonly code = 'vault.deposit.insufficient_trading_available'
  readonly status = 400

  constructor(
    message = 'Solde disponible insuffisant.',
    readonly available?: number,
    readonly requested?: number,
  ) {
    super(message)
    this.name = 'VaultDepositLimitError'
  }
}

function toNumber(value: unknown): number | undefined {
  if (value == null || value === '') return undefined
  const parsed = Number(String(value).replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : undefined
}

/** Lit trading_available USDC depuis la réponse `/api/app/crypto-positions/direct`. */
export function resolveTradingAvailableUsdcFromDirectPayload(raw: unknown): number {
  const root = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const list = Array.isArray(root.positions) ? root.positions : []
  for (const item of list) {
    if (!item || typeof item !== 'object') continue
    const row = item as Record<string, unknown>
    const asset = String(row.asset ?? '').trim().toUpperCase()
    if (asset !== 'USDC') continue
    const chainId = typeof row.chain_id === 'number' ? row.chain_id : null
    if (chainId != null && chainId !== BASE_CHAIN_ID) continue
    const trading = toNumber(row.trading_available)
    if (trading != null) return Math.max(0, trading)
    const platform = toNumber(row.platform_balance)
    if (platform != null && platform > 0) return platform
    return 0
  }
  for (const item of list) {
    if (!item || typeof item !== 'object') continue
    const row = item as Record<string, unknown>
    if (String(row.asset ?? '').trim().toUpperCase() !== 'USDC') continue
    const trading = toNumber(row.trading_available)
    if (trading != null) return Math.max(0, trading)
    const platform = toNumber(row.platform_balance)
    if (platform != null && platform > 0) return platform
    return 0
  }
  return 0
}

export function assertVaultDepositWithinTradingAvailable(args: {
  amount: number
  tradingAvailable: number
}): void {
  if (!Number.isFinite(args.amount) || args.amount <= 0) return
  const available = Math.max(0, args.tradingAvailable)
  if (args.amount > available + 1e-9) {
    throw new VaultDepositLimitError(
      'Solde disponible insuffisant.',
      available,
      args.amount,
    )
  }
}

export async function loadTradingAvailableUsdcForPortal(): Promise<number> {
  const { portalUpstreamFetch } = await import('@/lib/portal/portalUpstream')
  const res = await portalUpstreamFetch('/api/app/crypto-positions/direct', {
    signal: AbortSignal.timeout(15_000),
  })
  if (!res.ok) {
    throw new VaultDepositLimitError('Impossible de vérifier le solde disponible.', 0)
  }
  const data = await res.json().catch(() => null)
  return resolveTradingAvailableUsdcFromDirectPayload(data)
}

export async function assertPortalVaultDepositTradingAvailable(amount: string | number): Promise<void> {
  const numericAmount = typeof amount === 'number' ? amount : invParseAmount(amount)
  const tradingAvailable = await loadTradingAvailableUsdcForPortal()
  assertVaultDepositWithinTradingAvailable({ amount: numericAmount, tradingAvailable })
}
