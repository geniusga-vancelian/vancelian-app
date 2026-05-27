export function parseLombardHumanAmountToRaw(value: string, decimals: number): bigint {
  const normalized = value.trim().replace(',', '.')
  if (!/^\d+(\.\d+)?$/.test(normalized)) {
    throw new Error('Invalid amount.')
  }
  const [wholePart, fractionPart = ''] = normalized.split('.')
  const fraction = fractionPart.padEnd(decimals, '0').slice(0, decimals)
  const combined = `${wholePart}${fraction}`.replace(/^0+(?=\d)/, '')
  return BigInt(combined || '0')
}

export function rawToLombardHumanAmount(raw: bigint, decimals: number, maxFraction = 8): string {
  const base = BigInt(10) ** BigInt(Math.max(0, decimals))
  const whole = raw / base
  const fraction = raw % base
  if (fraction === BigInt(0)) return whole.toString()
  const fracStr = fraction.toString().padStart(decimals, '0').replace(/0+$/, '')
  const trimmed = fracStr.slice(0, maxFraction).replace(/0+$/, '')
  return trimmed ? `${whole}.${trimmed}` : whole.toString()
}

export function formatLombardTokenAmount(raw: bigint | string, decimals: number, maxFraction = 6): string {
  const value = typeof raw === 'string' ? BigInt(raw || '0') : raw
  return rawToLombardHumanAmount(value, decimals, maxFraction)
}

export function lltvWadToPercent(wad: bigint): number {
  return Math.round((Number(wad) / 1e16) * 100) / 100
}

export function formatLombardUsdAmount(value: string | number): string {
  const num = typeof value === 'string' ? Number(value.replace(',', '.')) : value
  if (!Number.isFinite(num)) return '—'
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 0,
  }).format(num)
}

export function formatLombardApyPercent(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return '—'
  return `${value.toFixed(1)}% variable`
}

export function formatLombardPercent(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return '—'
  return `${value.toFixed(0)}%`
}
