import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  LEDGITY_LYEURC_VAULT,
  LEDGITY_LYUSDC_VAULT,
  VANCELIAN_AXBALI_VAULT,
  VANCELIAN_AXDUBAI_VAULT,
  VANCELIAN_AXUSD_VAULT,
  VANCELIAN_VFEUR_VAULT,
  resolveKnownLedgityVaultAsset,
  resolveLedgityShareSymbol,
} from './ledgityConstants'

describe('resolveLedgityShareSymbol', () => {
  it('résout les symboles Vancelian/Arquantix mainnet', () => {
    assert.equal(resolveLedgityShareSymbol(VANCELIAN_VFEUR_VAULT), 'vfEUR')
    assert.equal(resolveLedgityShareSymbol(VANCELIAN_AXUSD_VAULT), 'axUSD')
    assert.equal(resolveLedgityShareSymbol(VANCELIAN_AXDUBAI_VAULT), 'axDUBAI')
    assert.equal(resolveLedgityShareSymbol(VANCELIAN_AXBALI_VAULT), 'axBALI')
  })

  it('résout les symboles Ledgity natifs', () => {
    assert.equal(resolveLedgityShareSymbol(LEDGITY_LYUSDC_VAULT), 'lyUSDC')
    assert.equal(resolveLedgityShareSymbol(LEDGITY_LYEURC_VAULT), 'lyEURC')
  })

  it('retombe sur ly{asset} pour un vault inconnu', () => {
    assert.equal(
      resolveLedgityShareSymbol('0x00000000000000000000000000000000000000aa', 'EURC'),
      'lyEURC',
    )
  })
})

describe('resolveKnownLedgityVaultAsset', () => {
  it('associe vfEUR et axDUBAI à EURC', () => {
    assert.equal(resolveKnownLedgityVaultAsset(VANCELIAN_VFEUR_VAULT)?.symbol, 'EURC')
    assert.equal(resolveKnownLedgityVaultAsset(VANCELIAN_AXDUBAI_VAULT)?.symbol, 'EURC')
  })

  it('associe axUSD à USDC', () => {
    assert.equal(resolveKnownLedgityVaultAsset(VANCELIAN_AXUSD_VAULT)?.symbol, 'USDC')
  })
})
