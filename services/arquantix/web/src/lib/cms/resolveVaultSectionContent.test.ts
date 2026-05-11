import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { ContentStatus } from '@prisma/client'

import { resolveVaultSectionContent } from './resolveVaultSectionContent'

function row(
  locale: string,
  status: ContentStatus,
  id: string,
): { locale: string; status: ContentStatus; id: string } {
  return { locale, status, id }
}

describe('resolveVaultSectionContent', () => {
  it('mode either : locale demandée pub puis draft', () => {
    const contents = [
      row('en', ContentStatus.DRAFT, 'a'),
      row('en', ContentStatus.PUBLISHED, 'b'),
    ]
    const r = resolveVaultSectionContent(contents, {
      requestedLocale: 'en',
      defaultLocale: 'fr',
      mode: 'either',
    })
    assert.equal(r?.id, 'b')
  })

  it('mode either : brouillon locale demandée avant fallback FR', () => {
    const contents = [
      row('fr', ContentStatus.PUBLISHED, 'fr-pub'),
      row('en', ContentStatus.DRAFT, 'en-draft'),
    ]
    const r = resolveVaultSectionContent(contents, {
      requestedLocale: 'en',
      defaultLocale: 'fr',
      mode: 'either',
    })
    assert.equal(r?.id, 'en-draft')
  })

  it('mode either : pas de ligne pour la locale → defaultLocale puis any', () => {
    const contents = [row('fr', ContentStatus.PUBLISHED, 'fr-pub')]
    const r = resolveVaultSectionContent(contents, {
      requestedLocale: 'en',
      defaultLocale: 'fr',
      mode: 'either',
    })
    assert.equal(r?.id, 'fr-pub')
  })

  it('mode either_draft_first : brouillon avant pub pour la même locale', () => {
    const contents = [
      row('en', ContentStatus.DRAFT, 'a'),
      row('en', ContentStatus.PUBLISHED, 'b'),
    ]
    const r = resolveVaultSectionContent(contents, {
      requestedLocale: 'en',
      defaultLocale: 'fr',
      mode: 'either_draft_first',
    })
    assert.equal(r?.id, 'a')
  })

  it('mode PUBLISHED : paliers sans mélanger draft', () => {
    const contents = [row('en', ContentStatus.DRAFT, 'd'), row('fr', ContentStatus.PUBLISHED, 'p')]
    const r = resolveVaultSectionContent(contents, {
      requestedLocale: 'en',
      defaultLocale: 'fr',
      mode: ContentStatus.PUBLISHED,
    })
    assert.equal(r?.id, 'p')
  })

  it('mode PUBLISHED : dernier recours autre locale', () => {
    const contents = [row('it', ContentStatus.PUBLISHED, 'it-only')]
    const r = resolveVaultSectionContent(contents, {
      requestedLocale: 'en',
      defaultLocale: 'fr',
      mode: ContentStatus.PUBLISHED,
    })
    assert.equal(r?.id, 'it-only')
  })

  it('mode DRAFT strict', () => {
    const contents = [
      row('fr', ContentStatus.PUBLISHED, 'pub'),
      row('en', ContentStatus.DRAFT, 'dr'),
    ]
    const r = resolveVaultSectionContent(contents, {
      requestedLocale: 'en',
      defaultLocale: 'fr',
      mode: ContentStatus.DRAFT,
    })
    assert.equal(r?.id, 'dr')
  })
})
