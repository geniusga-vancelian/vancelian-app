import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { buildPortalOfferHeroView, resolveHeroPhotos } from '@/lib/portal/offerDetailFormat'

function basePayload(
  contentModules: ExclusiveOfferVaultPayload['contentModules'],
): ExclusiveOfferVaultPayload {
  return {
    pageSlug: 'eo-test',
    pageTitle: 'Test',
    pageDescription: null,
    urlPath: '/projects/eo-test',
    locale: 'en',
    headerImageUrl: '/api/site/media/header-fallback',
    packagedProductId: null,
    productType: null,
    lending: null,
    vaultEngine: null,
    heroTitle: 'Hero title',
    heroSubtitle: null,
    tagPills: [],
    heroTags: ['Tag'],
    heroTitleSource: 'pageSeo',
    heroPromoVideoUrl: null,
    contentModules,
    modules: contentModules,
  }
}

describe('resolveHeroPhotos', () => {
  it('utilise le premier carrousel avec images résolues pour le hero', () => {
    const carouselId = 'carousel-1'
    const payload = basePayload([
      {
        id: carouselId,
        type: 'MediaImageCarouselModule',
        enabled: true,
        content: {
          moduleTitle: 'The Vision',
          carouselItems: [
            { mediaId: 'm1', url: '/api/site/media/m1', alt: null },
            { mediaId: 'm2', url: '/api/site/media/m2', alt: null },
          ],
        },
      },
    ])

    const { photos, heroCarouselModuleId } = resolveHeroPhotos(payload)
    assert.deepEqual(photos, ['/api/site/media/m1', '/api/site/media/m2'])
    assert.equal(heroCarouselModuleId, carouselId)
  })

  it('retombe sur headerImageUrl quand le carrousel est vide', () => {
    const payload = basePayload([
      {
        id: 'carousel-empty',
        type: 'MediaImageCarouselModule',
        enabled: true,
        content: { moduleTitle: '', imageMediaIds: [], carouselItems: [] },
      },
    ])

    const { photos, heroCarouselModuleId } = resolveHeroPhotos(payload)
    assert.deepEqual(photos, ['/api/site/media/header-fallback'])
    assert.equal(heroCarouselModuleId, null)
  })
})

describe('buildPortalOfferHeroView', () => {
  it('expose la vidéo promo TitlePage et priorise le hero vidéo sur les photos', () => {
    const payload = basePayload([])
    payload.heroPromoVideoUrl = 'https://www.youtube.com/watch?v=JpT4qLGlqzE'

    const hero = buildPortalOfferHeroView(payload)
    assert.equal(hero.promoVideoUrl, 'https://www.youtube.com/watch?v=JpT4qLGlqzE')
    assert.ok(hero.photos.length > 0)
  })
})
