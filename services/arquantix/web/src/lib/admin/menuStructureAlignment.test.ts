import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import type { MenuItem, Page } from '@prisma/client'

import {
  buildPostSyncItemOrder,
  extractMenuNavPageSequence,
  flattenNavTreePreorder,
  navOrderMatchesMenu,
} from './menuStructureAlignment'
import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'

function node(p: Partial<SiteTreeNode> & Pick<SiteTreeNode, 'id' | 'slug'>): SiteTreeNode {
  return {
    title: null,
    urlPath: `/${p.slug}`,
    template: 'homepage',
    parentId: null,
    sortOrder: 0,
    pageRole: 'STANDARD',
    showInNav: true,
    isSystemPage: false,
    children: [],
    packagedProduct: null,
    ...p,
  }
}

function mi(
  partial: Partial<MenuItem> & Pick<MenuItem, 'id' | 'order'>,
  page: Page | null,
): MenuItem & { page: Page | null } {
  return {
    menuId: 'm',
    label: 'L',
    enabled: true,
    isRoot: false,
    pageId: page?.id ?? null,
    type: 'LINK',
    buttonStyle: null,
    buttonAction: null,
    externalUrl: null,
    ...partial,
    page,
  } as MenuItem & { page: Page | null }
}

describe('menuStructureAlignment', () => {
  it('flattenNavTreePreorder — exclut home', () => {
    const tree = [
      node({
        id: 'h',
        slug: 'home',
        pageRole: 'HOME',
        showInNav: true,
        children: [node({ id: 'a', slug: 'about', parentId: 'h' })],
      }),
    ]
    tree[0].children[0].parentId = 'h'
    const flat = flattenNavTreePreorder(tree)
    assert.equal(flat.length, 1)
    assert.equal(flat[0].slug, 'about')
  })

  it('navOrderMatchesMenu', () => {
    assert.equal(navOrderMatchesMenu(['a', 'b'], ['a', 'b']), true)
    assert.equal(navOrderMatchesMenu(['a', 'b'], ['b', 'a']), false)
  })

  it('extractMenuNavPageSequence — ignore doublons même page', () => {
    const p = { id: 'p1', slug: 'x', title: null } as Page
    const items = [
      mi({ id: 'm1', order: 0, pageId: 'p1' }, p),
      mi({ id: 'm2', order: 1, pageId: 'p1' }, p),
    ]
    const seq = extractMenuNavPageSequence(items, ['p1'])
    assert.deepEqual(seq, ['p1'])
  })

  it('buildPostSyncItemOrder — racine puis nav puis reste', () => {
    const pa = { id: 'pa', slug: 'a', title: null, showInNav: true, template: 'homepage', urlPath: '/a' } as Page
    const pb = { id: 'pb', slug: 'b', title: null, showInNav: true, template: 'homepage', urlPath: '/b' } as Page
    const tree: SiteTreeNode[] = [
      node({
        id: 'r',
        slug: 'root',
        showInNav: false,
        children: [
          node({ id: 'pa', slug: 'a', showInNav: true }),
          node({ id: 'pb', slug: 'b', showInNav: true }),
        ],
      }),
    ]
    tree[0].children[0].parentId = 'r'
    tree[0].children[1].parentId = 'r'

    const items = [
      mi({ id: 'root', order: 0, isRoot: true, pageId: null, type: 'LINK' }, null),
      mi({ id: 'lb', order: 1, pageId: 'pb' }, pb),
      mi({ id: 'la', order: 2, pageId: 'pa' }, pa),
      mi({ id: 'btn', order: 3, type: 'BUTTON', pageId: null }, null),
    ]

    const ord = buildPostSyncItemOrder(items, tree)
    assert.deepEqual(ord, ['root', 'la', 'lb', 'btn'])
  })
})
