import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { buildLedgityLedgerMetadata, readLedgityPpsFromLedgerMetadata } from '@/lib/portal/ledgity/ledgityLedgerMetadata'
import { LEDGITY_LYEURC_VAULT } from '@/lib/portal/ledgity/ledgityConstants'

describe('ledgityLedgerMetadata', () => {
  it('maps lyEURC share symbol from vault address', () => {
    const metadata = buildLedgityLedgerMetadata({
      vaultAddress: LEDGITY_LYEURC_VAULT,
      assetSymbol: 'EURC',
      ppsAtTx: 1.05,
    }) as Record<string, unknown>

    assert.equal(metadata.share_symbol, 'lyEURC')
    assert.equal(readLedgityPpsFromLedgerMetadata(metadata), '1.05')
  })
})
