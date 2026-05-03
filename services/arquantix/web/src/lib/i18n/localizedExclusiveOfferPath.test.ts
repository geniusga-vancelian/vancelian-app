import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  getPublicLocaleFromPathname,
  localizedExclusiveOfferDetailPath,
  localizedProjectsHubPath,
} from '@/lib/i18n/localizedExclusiveOfferPath'

describe('localizedExclusiveOfferPath', () => {
  it('detail path includes locale', () => {
    assert.equal(localizedExclusiveOfferDetailPath('fr', 'niseko-mori-lodge'), '/fr/projects/niseko-mori-lodge')
    assert.equal(localizedExclusiveOfferDetailPath('en', 'foo'), '/en/projects/foo')
  })

  it('hub path includes locale', () => {
    assert.equal(localizedProjectsHubPath('it'), '/it/projects')
  })

  it('getPublicLocaleFromPathname reads first segment', () => {
    assert.equal(getPublicLocaleFromPathname('/fr/projects'), 'fr')
    assert.equal(getPublicLocaleFromPathname('/en/projects/foo'), 'en')
  })

  it('getPublicLocaleFromPathname falls back for non-prefixed paths', () => {
    assert.equal(getPublicLocaleFromPathname('/projects'), 'fr')
  })
})
