import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { ArticleBlockType } from '@prisma/client'

import { safeParseArticleBlockData } from '@/lib/blog/articleBlockDataSchemas'

describe('safeParseArticleBlockData', () => {
  it('rejette data non objet', () => {
    const r = safeParseArticleBlockData(ArticleBlockType.PARAGRAPH, [])
    assert.equal(r.success, false)
  })

  it('accepte paragraphe vide', () => {
    const r = safeParseArticleBlockData(ArticleBlockType.PARAGRAPH, {})
    assert.equal(r.success, true)
  })

  it('rejette items non tableau (liste)', () => {
    const r = safeParseArticleBlockData(ArticleBlockType.BULLET_LIST, { items: 'nope' })
    assert.equal(r.success, false)
  })

  it('accepte carrousel avec imageMediaIds vide', () => {
    const r = safeParseArticleBlockData(ArticleBlockType.MEDIA_IMAGE_CAROUSEL, {
      moduleTitle: '',
      imageMediaIds: [],
    })
    assert.equal(r.success, true)
  })

  it('accepte how_it_works_carousel vide (workflow « ajouter puis remplir »)', () => {
    const r = safeParseArticleBlockData(ArticleBlockType.HOW_IT_WORKS_CAROUSEL, {})
    assert.equal(r.success, true)
  })

  it('accepte how_it_works_carousel complet (calque section CMS)', () => {
    const r = safeParseArticleBlockData(ArticleBlockType.HOW_IT_WORKS_CAROUSEL, {
      label: 'HOW IT WORKS',
      title: 'A clear process',
      subtitle: 'In a few steps',
      hideStepNumbering: false,
      surface: 'light',
      steps: [
        { number: '01', title: 'Step 1', description: 'Lorem' },
        { number: '02', title: 'Step 2', description: 'Ipsum', stepButtonLabel: 'Go', stepButtonHref: '/x' },
      ],
      primaryCtaText: 'Start',
      primaryCtaHref: '/signup',
    })
    assert.equal(r.success, true)
  })

  it('rejette how_it_works_carousel avec steps non-tableau', () => {
    const r = safeParseArticleBlockData(ArticleBlockType.HOW_IT_WORKS_CAROUSEL, {
      steps: 'nope',
    })
    assert.equal(r.success, false)
  })

  it('rejette how_it_works_carousel avec surface invalide', () => {
    const r = safeParseArticleBlockData(ArticleBlockType.HOW_IT_WORKS_CAROUSEL, {
      surface: 'rainbow',
    })
    assert.equal(r.success, false)
  })

  it('rejette how_it_works_carousel avec hideStepNumbering non-booléen', () => {
    const r = safeParseArticleBlockData(ArticleBlockType.HOW_IT_WORKS_CAROUSEL, {
      hideStepNumbering: 'yes',
    })
    assert.equal(r.success, false)
  })
})
