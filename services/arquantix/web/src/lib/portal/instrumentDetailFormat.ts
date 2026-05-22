import { formatCryptoPrice, formatChangePct } from '@/lib/portal/marketsFormat'

export const CHART_PERIOD_OPTIONS = [
  { id: '1j', chip: '1D', caption: '1 day' },
  { id: '1s', chip: '1W', caption: '1 week' },
  { id: '1m', chip: '1M', caption: '1 month' },
  { id: '1a', chip: '1Y', caption: '1 year' },
  { id: '5a', chip: '5Y', caption: '5 years' },
] as const

export type ChartPeriodId = (typeof CHART_PERIOD_OPTIONS)[number]['id']

const SYMBOL_NAMES: Record<string, string> = {
  BTC: 'Bitcoin',
  ETH: 'Ether',
  SOL: 'Solana',
  XRP: 'XRP',
  BNB: 'BNB',
  ADA: 'Cardano',
  DOGE: 'Dogecoin',
  USDC: 'USD Coin',
  USDT: 'Tether',
  AVAX: 'Avalanche',
  LINK: 'Chainlink',
  DOT: 'Polkadot',
  TRX: 'Tron',
}

export function normalizeInstrumentTicker(raw: string): string {
  return raw.trim().toUpperCase()
}

/** Ticker court → symbole provider (BTC → BTCUSDT). Aligné Flutter `tickerToProviderSymbol`. */
export function tickerToProviderSymbol(ticker: string): string {
  const t = normalizeInstrumentTicker(ticker)
  if (!t) return 'BTCUSDT'
  if (t === 'USDT') return 'USDTUSDT'
  if (t.endsWith('USDT')) return t
  return `${t}USDT`
}

export function providerSymbolToTicker(symbol: string): string {
  const s = symbol.trim().toUpperCase()
  if (s === 'USDTUSDT') return 'USDT'
  if (s.endsWith('USDT')) return s.slice(0, -4)
  return s
}

export function instrumentDisplayName(ticker: string): string {
  const t = normalizeInstrumentTicker(ticker)
  return SYMBOL_NAMES[t] ?? t
}

export type InstrumentCandle = {
  open: number
  high: number
  low: number
  close: number
  ts?: string | number | null
}

export function parseInstrumentCandles(raw: unknown): InstrumentCandle[] {
  if (!Array.isArray(raw)) return []
  const candles: InstrumentCandle[] = []
  for (const row of raw) {
    const item = row as Record<string, unknown>
    const close = toNumber(item.close ?? item.c)
    if (close <= 0) continue
    candles.push({
      open: toNumber(item.open ?? item.o, close),
      high: toNumber(item.high ?? item.h, close),
      low: toNumber(item.low ?? item.l, close),
      close,
      ts: (item.ts ?? item.time ?? item.timestamp ?? null) as string | number | null,
    })
  }
  return candles
}

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  const parsed = Number.parseFloat(String(value ?? '').replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : fallback
}

export function periodPerformanceFromCandles(
  candles: InstrumentCandle[],
  currentPrice: number | null,
): { absUsd: number; pct: number } | null {
  if (candles.length === 0) return null
  const entry = candles[0]!.close
  if (entry <= 0) return null
  const current = currentPrice ?? candles[candles.length - 1]?.close
  if (current == null || current <= 0) return null
  const absUsd = current - entry
  return { absUsd, pct: (absUsd / entry) * 100 }
}

export function formatUsdAbsChange(value: number): string {
  const sign = value >= 0 ? '+' : '-'
  return `${sign}${formatCryptoPrice(Math.abs(value), 'USD')}`
}

export function formatPeriodCaption(periodId: ChartPeriodId): string {
  return CHART_PERIOD_OPTIONS.find((p) => p.id === periodId)?.caption ?? '1 day'
}

export function lineTrendPositive(candles: InstrumentCandle[]): boolean {
  if (candles.length >= 2) {
    return candles[candles.length - 1]!.close >= candles[0]!.close
  }
  if (candles.length === 1) {
    return candles[0]!.close >= candles[0]!.open
  }
  return true
}

export { formatChangePct, formatCryptoPrice }
