import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { ArticleBlockType } from '@prisma/client'

import { calculateReadingTime } from '@/lib/blog/readingTime'

describe('calculateReadingTime', () => {
  it('liste numérotée : compte les items', () => {
    const m = calculateReadingTime([
      {
        type: ArticleBlockType.NUMBERED_LIST,
        data: { items: ['un deux trois', 'quatre cinq'] },
      },
    ])
    assert.equal(m, 1)
  })

  it('DOCUMENT : compte le titre', () => {
    const m = calculateReadingTime([
      { type: ArticleBlockType.DOCUMENT, data: { mediaId: 'x', title: 'foo bar baz' } },
    ])
    assert.equal(m, 1)
  })

  it('IMAGE : compte la légende', () => {
    const m = calculateReadingTime([
      { type: ArticleBlockType.IMAGE, data: { mediaId: 'm', caption: 'Légende avec plusieurs mots' } },
    ])
    assert.equal(m, 1)
  })

  it('VIDEO : légende + bonus si URL', () => {
    const noUrl = calculateReadingTime([
      { type: ArticleBlockType.VIDEO, data: { url: '', caption: 'short' } },
    ])
    const withUrl = calculateReadingTime([
      { type: ArticleBlockType.VIDEO, data: { url: 'https://youtube.com/watch?v=abc', caption: '' } },
    ])
    assert.ok(withUrl >= noUrl)
    assert.equal(withUrl, 1)
  })

  it('paragraphe volumineux : au moins 2 minutes', () => {
    const longText = Array.from({ length: 500 }, () => 'word').join(' ')
    const m = calculateReadingTime([{ type: ArticleBlockType.PARAGRAPH, data: { text: longText } }])
    assert.ok(m >= 2)
  })

  it('aucun contenu textuel : minimum 1 minute', () => {
    assert.equal(
      calculateReadingTime([{ type: ArticleBlockType.HEADING, data: { text: '' } }]),
      1,
    )
  })
})
