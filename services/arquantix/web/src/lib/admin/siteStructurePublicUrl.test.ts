import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'
import { siteStructurePreviewUrl, siteStructurePublicUrl } from './siteStructurePublicUrl'
import {
  EXCLUSIVE_OFFER_GABARIT_SLUG,
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
  VAULT_BUILDER_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'

function node(partial: Partial<SiteTreeNode> & Pick<SiteTreeNode, 'slug' | 'urlPath' | 'template'>): SiteTreeNode {
  return {
    id: 'id',
    title: null,
    parentId: null,
    sortOrder: 0,
    pageRole: 'STANDARD',
    showInNav: true,
    isSystemPage: false,
    children: [],
    packagedProduct: null,
    ...partial,
  }
}

describe('siteStructurePublicUrl', () => {
  it('home → /{locale}', () => {
    assert.equal(
      siteStructurePublicUrl(node({ slug: 'home', urlPath: '/', template: 'homepage' }), 'fr'),
      '/fr',
    )
  })

  it('vault → /{locale}/projects/{slug}', () => {
    assert.equal(
      siteStructurePublicUrl(
        node({ slug: 'offre-x', urlPath: '/projects/offre-x', template: VAULT_BUILDER_TEMPLATE }),
        'fr',
      ),
      '/fr/projects/offre-x',
    )
  })

  it('vault par urlPath stocké /projects/{slug} (template non vault) → même URL localisée', () => {
    assert.equal(
      siteStructurePublicUrl(
        node({ slug: 'niseko-mori-lodge', urlPath: '/projects/niseko-mori-lodge', template: 'homepage' }),
        'fr',
      ),
      '/fr/projects/niseko-mori-lodge',
    )
  })

  it('locale vide → defaultLocale', () => {
    assert.equal(
      siteStructurePublicUrl(
        node({ slug: 'offre-x', urlPath: '/projects/offre-x', template: VAULT_BUILDER_TEMPLATE }),
        '',
      ),
      '/en/projects/offre-x',
    )
  })

  it('page CMS → /{locale}{urlPath}', () => {
    assert.equal(
      siteStructurePublicUrl(node({ slug: 'about', urlPath: '/about', template: 'homepage' }), 'en'),
      '/en/about',
    )
  })

  it('gabarit article → /{locale}/gabarit-preview/article', () => {
    assert.equal(
      siteStructurePublicUrl(
        node({
          slug: 'article',
          urlPath: '/article-template',
          template: 'article',
        }),
        'en',
      ),
      '/en/gabarit-preview/article',
    )
  })

  it('gabarit offre exclusive → /{locale}/gabarit-preview/exclusive-offer', () => {
    assert.equal(
      siteStructurePublicUrl(
        node({
          slug: EXCLUSIVE_OFFER_GABARIT_SLUG,
          urlPath: '/exclusive-offer-template',
          template: EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
        }),
        'fr',
      ),
      '/fr/gabarit-preview/exclusive-offer',
    )
  })

  it('article blog virtuel → /{locale}/blog/{slug}', () => {
    assert.equal(
      siteStructurePublicUrl(
        node({
          slug: 'mon-article',
          urlPath: '/blog/mon-article',
          template: 'blog_article',
          isVirtual: true,
          articleId: 'art1',
        }),
        'it',
      ),
      '/it/blog/mon-article',
    )
  })
})

describe('siteStructurePreviewUrl', () => {
  it('home → /preview/home?locale=…', () => {
    assert.equal(
      siteStructurePreviewUrl(node({ slug: 'home', urlPath: '/', template: 'homepage' }), 'en'),
      '/preview/home?locale=en',
    )
  })

  it('page CMS → /preview/{slug}?locale=…', () => {
    assert.equal(
      siteStructurePreviewUrl(node({ slug: 'about', urlPath: '/about', template: 'homepage' }), 'fr'),
      '/preview/about?locale=fr',
    )
  })

  it('vault → /preview/{slug}?locale=… (pas /{locale}/projects/…)', () => {
    assert.equal(
      siteStructurePreviewUrl(
        node({ slug: 'offre-x', urlPath: '/projects/offre-x', template: VAULT_BUILDER_TEMPLATE }),
        'en',
      ),
      '/preview/offre-x?locale=en',
    )
  })

  it('article blog virtuel → /preview/article/{id}?locale=…', () => {
    assert.equal(
      siteStructurePreviewUrl(
        node({
          slug: 'mon-article',
          urlPath: '/blog/mon-article',
          template: 'blog_article',
          isVirtual: true,
          articleId: 'art1',
        }),
        'fr',
      ),
      '/preview/article/art1?locale=fr',
    )
  })
})
