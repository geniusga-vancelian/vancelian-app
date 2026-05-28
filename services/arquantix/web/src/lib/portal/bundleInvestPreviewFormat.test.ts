import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  formatBundleInvestPreviewWarning,
  formatBundleInvestPreviewWarnings,
  parseBundleInvestPreviewWarning,
} from '@/lib/portal/bundleInvestPreviewFormat'

describe('bundleInvestPreviewFormat', () => {
  it('parses structured lifi preview warnings', () => {
    const raw =
      'lifi_preview_failed|asset=CBBTC|display=cbBTC|code=bundle.lifi.quote_failed|detail=No%20route'
    const parsed = parseBundleInvestPreviewWarning(raw)
    assert.equal(parsed.kind, 'lifi_preview_failed')
    assert.equal(parsed.asset, 'CBBTC')
    assert.equal(parsed.display, 'cbBTC')
    assert.equal(parsed.code, 'bundle.lifi.quote_failed')
    assert.equal(parsed.detail, 'No route')
  })

  it('formats lifi quote failure for users', () => {
    const msg = formatBundleInvestPreviewWarning(
      'lifi_preview_failed|asset=CBBTC|display=cbBTC|code=bundle.lifi.quote_failed|detail=Route%20unavailable',
    )
    assert.match(msg, /Cotation Li\.FI indisponible pour cbBTC/)
    assert.match(msg, /Route unavailable/)
  })

  it('formats missing person_id', () => {
    const msg = formatBundleInvestPreviewWarning(
      'lifi_preview_failed|asset=CBETH|display=cbETH|code=bundle.lifi.no_person_id|detail=Client%20sans%20person_id',
    )
    assert.match(msg, /Wallet Privy requis/)
  })

  it('maps legacy swap_preview_failed strings', () => {
    const msg = formatBundleInvestPreviewWarning(
      'swap_preview_failed:CBBTC: market_quote_stale: cbBTC quote is 537585s old (max 60s)',
    )
    assert.match(msg, /Prix marché expiré/)
    assert.match(msg, /cbBTC/)
  })

  it('joins multiple warnings', () => {
    const joined = formatBundleInvestPreviewWarnings([
      'lifi_preview_failed|asset=CBBTC|display=cbBTC|code=bundle.lifi.quote_failed|detail=x',
      'lifi_preview_failed|asset=CBETH|display=cbETH|code=bundle.lifi.quote_failed|detail=y',
    ])
    assert.ok(joined?.includes('\n'))
  })
})
