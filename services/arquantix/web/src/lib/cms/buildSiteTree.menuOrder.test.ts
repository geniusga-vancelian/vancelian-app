import assert from 'node:assert'
import { describe, it } from 'node:test'
import type { PageRole } from '@prisma/client'
import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'
import {
  extractPrimaryMenuPageIdOrder,
  orderSiteTreeLikePrimaryMenu,
} from '@/lib/cms/buildSiteTree'

function node(
  partial: Pick<SiteTreeNode, 'id' | 'slug' | 'sortOrder'> & {
    pageRole?: PageRole
    children?: SiteTreeNode[]
  },
): SiteTreeNode {
  return {
    title: null,
    urlPath: `/${partial.slug}`,
    template: 'homepage',
    parentId: null,
    pageRole: partial.pageRole ?? 'STANDARD',
    showInNav: true,
    isSystemPage: false,
    packagedProduct: null,
    children: partial.children ?? [],
    ...partial,
  }
}

describe('extractPrimaryMenuPageIdOrder', () => {
  const ctx = { homePageId: 'home-id' as string | null, blogPageId: null as string | null }

  it('respecte MenuItem.order comme la nav (accueil isRoot + liens)', () => {
    const ids = extractPrimaryMenuPageIdOrder(
      [
        {
          type: 'LINK',
          isRoot: true,
          pageId: null,
          order: 0,
          page: { template: 'homepage', slug: 'home' },
        },
        { type: 'LINK', isRoot: false, pageId: 'b', order: 2, page: { template: 'standard', slug: 'b' } },
        { type: 'LINK', isRoot: false, pageId: 'a', order: 1, page: { template: 'standard', slug: 'a' } },
        { type: 'LINK', isRoot: false, pageId: null, order: 3, page: null },
      ],
      ctx,
    )
    assert.deepStrictEqual(ids, ['home-id', 'a', 'b'])
  })

  it('inclut les entrées BUTTON avec pageId (lien interne)', () => {
    const ids = extractPrimaryMenuPageIdOrder(
      [
        {
          type: 'BUTTON',
          isRoot: false,
          pageId: 'x',
          order: 0,
          page: { template: 'standard', slug: 'x' },
          buttonStyle: 'text',
        },
      ],
      { homePageId: null, blogPageId: null },
    )
    assert.deepStrictEqual(ids, ['x'])
  })

  it('ajoute la page blog en queue si absente du menu (fallback layout)', () => {
    const ids = extractPrimaryMenuPageIdOrder(
      [
        {
          type: 'LINK',
          isRoot: true,
          pageId: null,
          order: 0,
          page: { template: 'homepage', slug: 'home' },
        },
        { type: 'LINK', isRoot: false, pageId: 'about', order: 1, page: { template: 'standard', slug: 'about' } },
      ],
      { homePageId: 'home-id', blogPageId: 'blog-id' },
    )
    assert.deepStrictEqual(ids, ['home-id', 'about', 'blog-id'])
  })
})

describe('orderSiteTreeLikePrimaryMenu', () => {
  it('réordonne la racine selon la séquence menu (comme le site)', () => {
    const roots = [
      node({ id: 'blog', slug: 'blog', sortOrder: 0 }),
      node({ id: 'home', slug: 'home', sortOrder: 0, pageRole: 'HOME' }),
      node({ id: 'about', slug: 'about', sortOrder: 0 }),
    ]
    const ordered = orderSiteTreeLikePrimaryMenu(roots, ['home', 'about', 'blog'])
    assert.deepStrictEqual(ordered.map((n) => n.slug), ['home', 'about', 'blog'])
  })

  it('ne force plus l’accueil en tête si le menu le place après d’autres liens', () => {
    const roots = [
      node({ id: 'blog', slug: 'blog', sortOrder: 0 }),
      node({ id: 'home', slug: 'home', sortOrder: 0, pageRole: 'HOME' }),
      node({ id: 'about', slug: 'about', sortOrder: 0 }),
    ]
    const ordered = orderSiteTreeLikePrimaryMenu(roots, ['about', 'home', 'blog'])
    assert.deepStrictEqual(ordered.map((n) => n.slug), ['about', 'home', 'blog'])
  })

  it('applique le même principe aux enfants', () => {
    const roots = [
      node({
        id: 'blog',
        slug: 'blog',
        sortOrder: 0,
        children: [
          node({ id: 'z', slug: 'z-child', sortOrder: 1 }),
          node({ id: 'y', slug: 'y-child', sortOrder: 0 }),
        ],
      }),
    ]
    const ordered = orderSiteTreeLikePrimaryMenu(roots, ['y', 'z'])
    assert.deepStrictEqual(
      ordered[0]!.children.map((c) => c.id),
      ['y', 'z'],
    )
  })
})
