import { PortfolioBar } from './types'

export interface CPPISeries {
  navSeries: Array<{ date: string; value: number }>
  floorSeries: Array<{ date: string; value: number }>
  riskyWeightSeriesPct: Array<{ date: string; value: number }>
}

export interface CPPIExtractionResult {
  hasData: boolean
  navSeries: Array<{ date: string; value: number }>
  floorSeries: Array<{ date: string; value: number }>
  riskyWeightSeriesPct: Array<{ date: string; value: number }>
  error?: string
}

/**
 * Extract CPPI series from portfolio bars
 * @param portfolio - Array of portfolio bars
 * @param strategyParams - Optional strategy params to compute static floor if needed
 * @returns CPPI series data
 */
export function extractCPPISeries(
  portfolio: PortfolioBar[],
  strategyParams?: {
    floor_ratio?: number
  }
): CPPIExtractionResult {
  if (!portfolio || portfolio.length === 0) {
    console.log('[CPPI Extract] No portfolio data')
    return {
      hasData: false,
      navSeries: [],
      floorSeries: [],
      riskyWeightSeriesPct: [],
      error: 'No portfolio data available',
    }
  }

  // Diagnostic: log first bar structure
  if (portfolio.length > 0) {
    console.log('[CPPI Extract] First portfolio bar sample:', {
      date: portfolio[0].date,
      nav_base100: portfolio[0].nav_base100,
      has_weights_json: !!portfolio[0].weights_json,
      weights_json_keys: portfolio[0].weights_json ? Object.keys(portfolio[0].weights_json) : [],
      weights_json_cppi: portfolio[0].weights_json ? {
        _cppi_risky_weight: portfolio[0].weights_json._cppi_risky_weight,
        _cppi_floor: portfolio[0].weights_json._cppi_floor,
        _cppi_cushion: portfolio[0].weights_json._cppi_cushion,
      } : null,
    })
  }

  const navSeries: Array<{ date: string; value: number }> = []
  const floorSeries: Array<{ date: string; value: number }> = []
  const riskyWeightSeriesPct: Array<{ date: string; value: number }> = []

  let hasRiskyWeightData = false
  let hasFloorData = false

  for (const bar of portfolio) {
    const date = bar.date

    // Extract NAV
    const nav = bar.nav_base100
    if (nav != null) {
      navSeries.push({ date, value: nav })
    }

    // Extract CPPI weights from weights_json
    if (bar.weights_json) {
      const weights = bar.weights_json

      // Extract risky weight (0..1 -> percentage)
      if (weights._cppi_risky_weight != null) {
        const riskyWeightPct = Number(weights._cppi_risky_weight) * 100
        riskyWeightSeriesPct.push({ date, value: riskyWeightPct })
        hasRiskyWeightData = true
      }

      // Extract floor (base100 level)
      if (weights._cppi_floor != null) {
        const floor = Number(weights._cppi_floor)
        floorSeries.push({ date, value: floor })
        hasFloorData = true
      }
    }

  }

  // Fallback: if no floor data in weights_json but floor_ratio is available, compute static floor
  if (!hasFloorData && strategyParams?.floor_ratio != null) {
    // Compute static floor from floor_ratio (floor_ratio * 100 for base100)
    const staticFloor = strategyParams.floor_ratio * 100
    // Fill all dates with static floor
    for (const nav of navSeries) {
      if (!floorSeries.find(f => f.date === nav.date)) {
        floorSeries.push({ date: nav.date, value: staticFloor })
      }
    }
    // Sort again
    floorSeries.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    hasFloorData = floorSeries.length > 0
  }

  // Sort series by date
  navSeries.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  floorSeries.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  riskyWeightSeriesPct.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  const hasData = navSeries.length > 0 && (hasRiskyWeightData || hasFloorData)

  console.log('[CPPI Extract] Extraction result:', {
    hasData,
    navSeries_length: navSeries.length,
    floorSeries_length: floorSeries.length,
    riskyWeightSeriesPct_length: riskyWeightSeriesPct.length,
    hasRiskyWeightData,
    hasFloorData,
  })

  return {
    hasData,
    navSeries,
    floorSeries,
    riskyWeightSeriesPct,
    error: !hasData && portfolio.length > 0 ? 'CPPI data not found in portfolio series' : undefined,
  }
}
