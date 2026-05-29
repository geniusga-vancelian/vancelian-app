import { describe, expect, it } from 'vitest'

import { parseBundleChartPoints } from './bundleProductFormat'

describe('parseBundleChartPoints', () => {
  it('lit la forme backend (points + performance_pct)', () => {
    const parsed = parseBundleChartPoints({
      performance_pct: 1.25,
      points: [{ value: 100 }, { value: 101.25 }],
    })
    expect(parsed.historyPoints).toEqual([100, 101.25])
    expect(parsed.performancePct).toBe(1.25)
  })

  it('lit la forme BFF portal (historyPoints + performancePct)', () => {
    const parsed = parseBundleChartPoints({
      period: '1j',
      performancePct: 0.59,
      historyPoints: [100, 99.8, 100.6],
    })
    expect(parsed.historyPoints).toEqual([100, 99.8, 100.6])
    expect(parsed.performancePct).toBe(0.59)
  })
})
