import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { ContentStatus } from '@prisma/client'

import {
  resolveVaultSectionContent,
  resolveVaultSectionContentForCatalog,
  resolveVaultSectionContentForExclusiveOfferPayload,
} from './resolveVaultSectionContent'

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

describe('resolveVaultSectionContentForCatalog', () => {
  it('FR vide + EN rempli → sert EN (app en locale fr)', () => {
    const contents = [
      {
        locale: 'fr',
        status: ContentStatus.PUBLISHED,
        id: 'fr-pub',
        data: { modules: [] },
      },
      {
        locale: 'en',
        status: ContentStatus.PUBLISHED,
        id: 'en-pub',
        data: { modules: [{ type: 'StepsModule' }] },
      },
    ]
    const r = resolveVaultSectionContentForCatalog(contents, {
      requestedLocale: 'fr',
      defaultLocale: 'fr',
    })
    assert.equal(r?.id, 'en-pub')
  })

  it('pub FR sans modules mais brouillon FR rempli → reste intra-FR', () => {
    const contents = [
      {
        locale: 'fr',
        status: ContentStatus.PUBLISHED,
        id: 'fr-pub',
        data: { modules: [] },
      },
      {
        locale: 'fr',
        status: ContentStatus.DRAFT,
        id: 'fr-draft',
        data: { modules: [{ type: 'A' }] },
      },
    ]
    const r = resolveVaultSectionContentForCatalog(contents, {
      requestedLocale: 'fr',
      defaultLocale: 'fr',
    })
    assert.equal(r?.id, 'fr-draft')
  })
})

describe('resolveVaultSectionContentForExclusiveOfferPayload', () => {
  it('public : aligné catalogue — FR vide + EN rempli (defaultLocale en)', () => {
    const contents = [
      {
        locale: 'fr',
        status: ContentStatus.PUBLISHED,
        id: 'fr-pub',
        data: { modules: [] },
      },
      {
        locale: 'en',
        status: ContentStatus.PUBLISHED,
        id: 'en-pub',
        data: { modules: [{ type: 'StepsModule' }] },
      },
    ]
    const r = resolveVaultSectionContentForExclusiveOfferPayload(contents, {
      requestedLocale: 'fr',
      defaultLocale: 'en',
      previewDraftFirst: false,
    })
    assert.equal(r?.id, 'en-pub')
  })

  it('preview draft-first : préfère EN brouillon lorsque FR totalement vide', () => {
    const contents = [
      {
        locale: 'fr',
        status: ContentStatus.PUBLISHED,
        id: 'fr-pub',
        data: { modules: [] },
      },
      {
        locale: 'fr',
        status: ContentStatus.DRAFT,
        id: 'fr-draft',
        data: { modules: [] },
      },
      {
        locale: 'en',
        status: ContentStatus.PUBLISHED,
        id: 'en-pub',
        data: { modules: [{ type: 'PARAGRAPH' }] },
      },
      {
        locale: 'en',
        status: ContentStatus.DRAFT,
        id: 'en-draft',
        data: { modules: [{ type: 'StepsModule' }] },
      },
    ]
    const r = resolveVaultSectionContentForExclusiveOfferPayload(contents, {
      requestedLocale: 'fr',
      defaultLocale: 'en',
      previewDraftFirst: true,
    })
    assert.equal(r?.id, 'en-draft')
  })
})
