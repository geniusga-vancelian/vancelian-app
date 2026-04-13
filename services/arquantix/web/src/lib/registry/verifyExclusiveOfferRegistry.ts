/**
 * Vérification statique du registre Exclusive Offers (Phase 8).
 * Cohérence Prisma uniquement (pas d’appel catalogue HTTP).
 */
import type { PackagedEngineType, PackagedProduct } from '@prisma/client'
import type { PrismaClient } from '@prisma/client'

import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'

export type VerifySeverity = 'error' | 'warning'

export type VerifyAnomaly = {
  severity: VerifySeverity
  code: string
  message: string
  packagedProductId: string
  slug: string
  meta?: Record<string, unknown>
}

export type VerifyExclusiveOfferReport = {
  status: 'ok' | 'fail'
  scanned: number
  anomalies: VerifyAnomaly[]
  generatedAt: string
}

type PageSlice = { id: string; slug: string; template: string }

/** Vérifs ne dépendant pas des jointures lending (tests unitaires). */
export function verifyPackagedProductPageAndSlug(
  row: Pick<PackagedProduct, 'id' | 'slug' | 'productType'> & { page: PageSlice | null },
): VerifyAnomaly[] {
  const out: VerifyAnomaly[] = []
  const slug = row.slug ?? ''

  if (!slug.trim()) {
    out.push({
      severity: 'error',
      code: 'EMPTY_SLUG',
      message: 'Slug packagé vide',
      packagedProductId: row.id,
      slug,
    })
  }

  if (!row.page) {
    out.push({
      severity: 'error',
      code: 'PAGE_MISSING',
      message: 'Page liée introuvable',
      packagedProductId: row.id,
      slug,
    })
    return out
  }

  if (row.page.template !== VAULT_BUILDER_TEMPLATE) {
    out.push({
      severity: 'error',
      code: 'PAGE_NOT_VAULT_BUILDER',
      message: `Page attendue template "${VAULT_BUILDER_TEMPLATE}", reçu "${row.page.template}"`,
      packagedProductId: row.id,
      slug,
      meta: { pageId: row.page.id },
    })
  }

  return out
}

async function verifyLendingEngine(
  prisma: PrismaClient,
  row: PackagedProduct & { page: PageSlice | null },
): Promise<VerifyAnomaly[]> {
  const out: VerifyAnomaly[] = []
  const slug = row.slug ?? ''

  const lppByPackaged = await prisma.lendingPoolProducts.findFirst({
    where: { packagedProductId: row.id },
  })

  if (row.engineType === ('LENDING' satisfies PackagedEngineType)) {
    const ref = row.engineReferenceId?.trim()
    if (!ref) {
      out.push({
        severity: 'error',
        code: 'LENDING_MISSING_ENGINE_REFERENCE',
        message: 'engine_type=LENDING mais engine_reference_id absent',
        packagedProductId: row.id,
        slug,
      })
      return out
    }

    const lpp = await prisma.lendingPoolProducts.findUnique({
      where: { id: ref },
    })

    if (!lpp) {
      out.push({
        severity: 'error',
        code: 'LENDING_POOL_PRODUCT_NOT_FOUND',
        message: `lending_pool_products introuvable pour id=${ref}`,
        packagedProductId: row.id,
        slug,
      })
      return out
    }

    if (lpp.packagedProductId !== row.id) {
      out.push({
        severity: 'error',
        code: 'LENDING_PACKAGED_PRODUCT_ID_MISMATCH',
        message: 'lending_pool_products.packaged_product_id ne correspond pas à ce packaged product',
        packagedProductId: row.id,
        slug,
        meta: { expectedPackagedId: row.id, actual: lpp.packagedProductId },
      })
    }

    if (lppByPackaged && lppByPackaged.id !== lpp.id) {
      out.push({
        severity: 'error',
        code: 'LENDING_DUPLICATE_LINK',
        message:
          'Deux rattachements lending possibles : packaged_product_id et engine_reference_id divergent',
        packagedProductId: row.id,
        slug,
        meta: { byPackagedId: lppByPackaged.id, byEngineId: lpp.id },
      })
    }
  } else if (lppByPackaged) {
    out.push({
      severity: 'warning',
      code: 'LENDING_ROW_WITHOUT_LENDING_ENGINE',
      message: 'lending_pool_products lié par packaged_product_id mais engine_type ≠ LENDING',
      packagedProductId: row.id,
      slug,
      meta: { engineType: row.engineType ?? null, lendingPoolProductId: lppByPackaged.id },
    })
  }

  return out
}

export async function verifyExclusiveOfferRegistry(prisma: PrismaClient): Promise<VerifyExclusiveOfferReport> {
  const rows = await prisma.packagedProduct.findMany({
    where: { productType: 'EXCLUSIVE_OFFER' },
    include: {
      page: { select: { id: true, slug: true, template: true } },
    },
  })

  const anomalies: VerifyAnomaly[] = []
  for (const row of rows) {
    anomalies.push(...verifyPackagedProductPageAndSlug(row))
    anomalies.push(...(await verifyLendingEngine(prisma, row)))
  }

  const errors = anomalies.filter((a) => a.severity === 'error')
  return {
    status: errors.length === 0 ? 'ok' : 'fail',
    scanned: rows.length,
    anomalies,
    generatedAt: new Date().toISOString(),
  }
}
