import { invParseAmount, resolveVaultDepositUsdcFromRows } from '@/lib/portal/portalInvestFlowFormat'

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
  const rows = list
    .filter((item): item is Record<string, unknown> => item != null && typeof item === 'object')
    .map((row) => ({
      asset: String(row.asset ?? ''),
      chainId: typeof row.chain_id === 'number' ? row.chain_id : null,
      tradingAvailable: toNumber(row.trading_available),
      platformBalance: toNumber(row.platform_balance),
    }))
  return resolveVaultDepositUsdcFromRows(rows)
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
