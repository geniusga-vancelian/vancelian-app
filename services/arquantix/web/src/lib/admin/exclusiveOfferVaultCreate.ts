/**
 * Création atomique page Vault Builder + PackagedProduct EXCLUSIVE_OFFER (admin Phase 8Bis).
 * Aligné sur POST /api/admin/vaults pour le contenu de section.
 */
import {
  ContentStatus,
  PackagedCommercialStatus,
  PackagedProductType,
  PackagedVisibility,
  Prisma,
} from '@prisma/client'

import { calculateUrlPath, isValidSlug } from '@/lib/utils/slugify'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'
const VAULT_DEFAULT_LOCALE = 'fr'

/** Même structure par défaut que `buildDefaultConfig()` dans api/admin/vaults/route.ts */
export function defaultVaultBuilderSectionData(): Record<string, unknown> {
  return {
    templateKey: 'PageSimpleNavBarTopTitlePageContent',
    navbar: {
      leftIconType: 'back',
      leftRedirectType: 'back',
      leftTarget: '',
      rightAction: {
        icon: 'favorite',
        redirectType: 'none',
        target: '',
      },
    },
    pageTitle: {
      enabled: true,
      text: 'Titre de page',
    },
    fixedBottomCta: {
      enabled: false,
      label: 'Parrainer une entreprise',
      redirectType: 'none',
      target: '',
    },
    modules: [],
    investmentTypeSlug: undefined,
    sortOrder: 0,
  }
}

export interface CreateExclusiveOfferVaultInput {
  slug: string
  title: string
  description: string | null
}

export async function createExclusiveOfferVaultInTransaction(
  tx: Prisma.TransactionClient,
  input: CreateExclusiveOfferVaultInput
): Promise<{ pageId: string; slug: string; packagedProductId: string }> {
  const slug = input.slug.trim()
  if (!isValidSlug(slug)) {
    throw new Error('Slug invalide.')
  }
  const urlPath = calculateUrlPath(slug)
  const configWithMeta = defaultVaultBuilderSectionData()

  const page = await tx.page.create({
    data: {
      slug,
      urlPath,
      title: input.title.trim() || slug,
      description: input.description,
      template: VAULT_TEMPLATE_DB,
      sections: {
        create: {
          key: VAULT_SECTION_KEY,
          order: 0,
          schemaVersion: 'v1',
          contents: {
            create: [
              {
                locale: VAULT_DEFAULT_LOCALE,
                status: ContentStatus.DRAFT,
                data: configWithMeta as Prisma.InputJsonValue,
              },
              {
                locale: VAULT_DEFAULT_LOCALE,
                status: ContentStatus.PUBLISHED,
                data: configWithMeta as Prisma.InputJsonValue,
              },
            ],
          },
        },
      },
    },
  })

  const packaged = await tx.packagedProduct.create({
    data: {
      slug,
      pageId: page.id,
      productType: PackagedProductType.EXCLUSIVE_OFFER,
      commercialStatus: PackagedCommercialStatus.DRAFT,
      visibility: PackagedVisibility.PUBLIC,
      featuredRank: null,
      categorySlug: null,
    },
  })

  return { pageId: page.id, slug: page.slug, packagedProductId: packaged.id }
}
