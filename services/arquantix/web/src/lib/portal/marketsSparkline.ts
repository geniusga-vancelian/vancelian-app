/** Mini line chart marchés — 1 point par heure sur les dernières 24 h. */
export const MARKETS_SPARKLINE_HOURLY_POINTS = 24

export function parseRawSparkline24h(raw: unknown): number[] {
  if (!Array.isArray(raw)) return []
  const out: number[] = []
  for (const item of raw) {
    const n = typeof item === 'number' ? item : Number(String(item).replace(',', '.'))
    if (Number.isFinite(n)) out.push(n)
  }
  return out
}

/**
 * Réduit la série backend (closes 5 min, jusqu'à ~288 points) en exactement
 * {@link MARKETS_SPARKLINE_HOURLY_POINTS} closes horaires (dernier close par bucket).
 */
export function downsampleSparklineToHourlyPoints(
  values: number[],
  points = MARKETS_SPARKLINE_HOURLY_POINTS,
): number[] {
  if (values.length === 0 || points < 2) return []

  if (values.length === points) return [...values]

  if (values.length < points) {
    const out: number[] = []
    for (let i = 0; i < points; i += 1) {
      const t = (i / (points - 1)) * (values.length - 1)
      const lo = Math.floor(t)
      const hi = Math.min(lo + 1, values.length - 1)
      const frac = t - lo
      out.push(values[lo]! * (1 - frac) + values[hi]! * frac)
    }
    return out
  }

  const out: number[] = []
  const bucketSize = values.length / points
  for (let i = 0; i < points; i += 1) {
    const start = Math.floor(i * bucketSize)
    const end = Math.min(Math.floor((i + 1) * bucketSize), values.length)
    const slice = values.slice(start, Math.max(end, start + 1))
    out.push(slice[slice.length - 1]!)
  }
  return out
}

/** Sparkline synthétique — fallback quand l’API ne fournit pas encore de série. */
export function buildSyntheticMarketsSparklineValues(
  ticker: string,
  changePct: number,
  points = MARKETS_SPARKLINE_HOURLY_POINTS,
): number[] {
  let h = 0
  for (let i = 0; i < ticker.length; i += 1) {
    h = (h * 31 + ticker.charCodeAt(i)) >>> 0
  }

  const rng = () => {
    h = (h * 9301 + 49297) % 233280
    return h / 233280
  }

  const values: number[] = []
  let v = 100
  for (let i = 0; i < points; i += 1) {
    const trend = (changePct / 100) * (i / (points - 1)) * 3
    v += (rng() - 0.5) * 4 + trend
    values.push(v)
  }
  return values
}

export function mapSparkline24hFromRow(raw: unknown): number[] {
  return downsampleSparklineToHourlyPoints(parseRawSparkline24h(raw))
}

export function resolveMarketsSparklineValues(args: {
  sparkline24h?: number[]
  ticker: string
  changePct: number
}): number[] {
  const fromApi = (args.sparkline24h ?? []).filter((value) => Number.isFinite(value))
  if (fromApi.length >= 2) {
    return downsampleSparklineToHourlyPoints(fromApi)
  }
  return buildSyntheticMarketsSparklineValues(args.ticker, args.changePct)
}

/** @deprecated Alias historique — préférer buildSyntheticMarketsSparklineValues. */
export const buildMarketsSparklineValues = buildSyntheticMarketsSparklineValues
