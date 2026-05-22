/**
 * Le Vault Builder admin enregistre les modules « produit (bundle / PE) » dans
 * `portfolio_product_configs`, alors que l’app mobile lit `vault.data` depuis le
 * SectionContent `vault_builder_v1`. Quand les deux identifiants coïncident
 * (ex. `legacy_project_id`, `lending_pool_products.project_id` ou le slug page,
 * si l’un d’eux coïncide avec `product_code` en base PE), on fusionne pour que le Markdown et les autres modules produit
 * apparaissent dans le même flux que le vault page.
 */
import type { PrismaClient } from '@prisma/client'

import type { VaultModulePublic } from '@/lib/cms/exclusiveOfferVaultPage'
import { normalizeVaultModulesArray } from '@/lib/vault/normalizeVaultModules'

export type PackagedForPortfolioVaultMerge = {
  slug: string
  legacyProjectId: string | null
  lendingPoolProduct: { projectId: string | null } | null
}

function uniqueCandidates(candidates: Array<string | null | undefined>): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const raw of candidates) {
    const s = typeof raw === 'string' ? raw.trim() : ''
    if (!s || seen.has(s)) continue
    seen.add(s)
    out.push(s)
  }
  return out
}

/**
 * Résolution best-effort : pas de lien Prisma direct Packaged ↔ product_code PE.
 */
export function portfolioProductCodeCandidatesForMerge(packaged: PackagedForPortfolioVaultMerge): string[] {
  return uniqueCandidates([
    packaged.lendingPoolProduct?.projectId,
    packaged.legacyProjectId,
    packaged.slug,
  ])
}

export async function fetchPortfolioModulesRawForMerge(
  prisma: PrismaClient,
  packaged: PackagedForPortfolioVaultMerge,
): Promise<unknown[]> {
  const codes = portfolioProductCodeCandidatesForMerge(packaged)
  for (const productCode of codes) {
    const row = await prisma.portfolioProductConfig.findUnique({
      where: { productCode },
      select: { modules: true },
    })
    const m = row?.modules
    if (Array.isArray(m) && m.length > 0) {
      return m as unknown[]
    }
  }
  return []
}

/**
 * Normalise les modules produit comme le JSON vault, puis les concatène après
 * les modules vault déjà normalisés.
 */
export function appendNormalizedPortfolioModules(
  vaultModules: VaultModulePublic[],
  portfolioRaw: unknown[],
  contextSlug: string,
): { merged: VaultModulePublic[]; warnings: string[] } {
  if (portfolioRaw.length === 0) {
    return { merged: vaultModules, warnings: [] }
  }
  const { modules: extra, warnings } = normalizeVaultModulesArray(portfolioRaw, `${contextSlug}:portfolio`)
  const merged = [...vaultModules, ...(extra as VaultModulePublic[])]
  return { merged, warnings }
}
