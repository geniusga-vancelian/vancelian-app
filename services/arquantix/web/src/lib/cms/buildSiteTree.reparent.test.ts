import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { PackagedProductType } from '@prisma/client'
import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'
import {
  EXCLUSIVE_OFFER_GABARIT_SLUG,
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
  VAULT_BUILDER_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'
import { reparentExclusiveOfferVaultsUnderGabarit } from '@/lib/cms/buildSiteTree'

function base(partial: Partial<SiteTreeNode> & Pick<SiteTreeNode, 'id' | 'slug'>): SiteTreeNode {
  return {
    title: null,
    urlPath: `/${partial.slug}`,
    template: 'homepage',
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

describe('reparentExclusiveOfferVaultsUnderGabarit', () => {
  it('déplace les vaults EO sous le gabarit exclusive-offer', () => {
    const gabarit = base({
      id: 'g',
      slug: EXCLUSIVE_OFFER_GABARIT_SLUG,
      template: EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
      children: [],
    })
    const eoVault = base({
      id: 'eo1',
      slug: 'bali-offer',
      template: VAULT_BUILDER_TEMPLATE,
      packagedProduct: {
        id: 'pp1',
        slug: 'bali-offer',
        productType: PackagedProductType.EXCLUSIVE_OFFER,
      },
      children: [],
    })
    const hub = base({
      id: 'hub',
      slug: 'projects',
      pageRole: 'PROJECTS_HUB',
      children: [gabarit, eoVault],
    })

    const out = reparentExclusiveOfferVaultsUnderGabarit([hub])
    assert.equal(out[0]!.children.length, 1)
    assert.equal(out[0]!.children[0]!.slug, EXCLUSIVE_OFFER_GABARIT_SLUG)
    const g2 = out[0]!.children[0]!
    assert.equal(g2.children.length, 1)
    assert.equal(g2.children[0]!.id, 'eo1')
  })
})
