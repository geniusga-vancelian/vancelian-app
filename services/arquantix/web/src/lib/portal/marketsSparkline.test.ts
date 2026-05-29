import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  MARKETS_SPARKLINE_HOURLY_POINTS,
  buildSyntheticMarketsSparklineValues,
  downsampleSparklineToHourlyPoints,
  mapSparkline24hFromRow,
  resolveMarketsSparklineValues,
} from '@/lib/portal/marketsSparkline'

describe('marketsSparkline', () => {
  it('downsamples ~288 5m closes to 24 hourly points', () => {
    const bars5m = Array.from({ length: 288 }, (_, index) => 100 + index * 0.1)
    const hourly = downsampleSparklineToHourlyPoints(bars5m)
    assert.equal(hourly.length, MARKETS_SPARKLINE_HOURLY_POINTS)
    assert.equal(hourly[0], bars5m[11])
    assert.equal(hourly[hourly.length - 1], bars5m[bars5m.length - 1])
  })

  it('keeps a 24-point series unchanged', () => {
    const series = Array.from({ length: 24 }, (_, index) => index)
    assert.deepEqual(downsampleSparklineToHourlyPoints(series), series)
  })

  it('interpolates sparse series up to 24 points', () => {
    const sparse = [10, 20, 30]
    const hourly = downsampleSparklineToHourlyPoints(sparse)
    assert.equal(hourly.length, MARKETS_SPARKLINE_HOURLY_POINTS)
    assert.equal(hourly[0], 10)
    assert.equal(hourly[hourly.length - 1], 30)
  })

  it('maps sparkline_24h from API rows', () => {
    const mapped = mapSparkline24hFromRow([100, 101, 102, 103])
    assert.equal(mapped.length, MARKETS_SPARKLINE_HOURLY_POINTS)
  })

  it('falls back to synthetic sparkline when API data is missing', () => {
    const synthetic = resolveMarketsSparklineValues({
      ticker: 'ETH',
      changePct: 1.2,
    })
    assert.equal(synthetic.length, MARKETS_SPARKLINE_HOURLY_POINTS)
    assert.notDeepEqual(
      resolveMarketsSparklineValues({ ticker: 'BTC', changePct: 1.2 }),
      resolveMarketsSparklineValues({ ticker: 'ETH', changePct: 1.2 }),
    )
  })

  it('builds deterministic synthetic values for a ticker', () => {
    const first = buildSyntheticMarketsSparklineValues('LINK', -0.5)
    const second = buildSyntheticMarketsSparklineValues('LINK', -0.5)
    assert.deepEqual(first, second)
    assert.equal(first.length, MARKETS_SPARKLINE_HOURLY_POINTS)
  })
})
