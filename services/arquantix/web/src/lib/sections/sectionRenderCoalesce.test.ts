import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  aboutFamilyToProps,
  ctaPrimaryFromLegacy,
  heroBackgroundOpacity01,
  heroResolvedBackgroundUrl,
  projectGridLegacyItemToProp,
} from '@/lib/sections/sectionRenderCoalesce'

describe('sectionRenderCoalesce — contrats stables', () => {
  it('heroBackgroundOpacity01 : défaut 1, string numérique, bornes', () => {
    assert.equal(heroBackgroundOpacity01(undefined), 1)
    assert.equal(heroBackgroundOpacity01('0.5'), 0.5)
    assert.equal(heroBackgroundOpacity01(2), 1)
    assert.equal(heroBackgroundOpacity01(-1), 0)
  })

  it('heroResolvedBackgroundUrl : trim', () => {
    assert.equal(heroResolvedBackgroundUrl({ backgroundMediaUrl: '  x  ' }), 'x')
    assert.equal(heroResolvedBackgroundUrl({}), '')
  })

  it('ctaPrimaryFromLegacy : || (chaîne vide → fallback)', () => {
    assert.deepStrictEqual(
      ctaPrimaryFromLegacy({
        primaryButtonText: '',
        ctaText: 'A',
        primaryButtonHref: '',
        ctaLink: '/b',
      }),
      { primaryButtonText: 'A', primaryButtonHref: '/b' },
    )
    assert.deepStrictEqual(
      ctaPrimaryFromLegacy({
        primaryButtonText: 'P',
        ctaText: 'A',
        primaryButtonHref: '/p',
        ctaLink: '/b',
      }),
      { primaryButtonText: 'P', primaryButtonHref: '/p' },
    )
  })

  it('aboutFamilyToProps : imageMediaUrl prioritaire', () => {
    assert.equal(
      aboutFamilyToProps({
        imageMediaUrl: 'm',
        imageUrl: 'u',
      }).imageUrl,
      'm',
    )
  })

  it('projectGridLegacyItemToProp', () => {
    const o = projectGridLegacyItemToProp({ title: 't', mediaUrl: 'https://x' })
    assert.equal(o.backgroundImage, 'https://x')
    assert.equal(o.title, 't')
  })
})
