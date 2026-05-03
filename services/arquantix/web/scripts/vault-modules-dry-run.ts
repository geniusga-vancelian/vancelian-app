/**
 * Lecture seule : inventaire des modules vault publiés, warnings de normalisation,
 * et écart catalogue admin vs renderer web.
 *
 * Usage : `npx tsx scripts/vault-modules-dry-run.ts`
 */

import { ContentStatus, PrismaClient } from '@prisma/client'

import { VAULT_BUILDER_TEMPLATE, VAULT_SECTION_KEY } from '@/lib/catalog/packagedCatalogHelpers'
import {
  hasWebExplicitRenderer,
  isAdminRegisteredVaultModuleType,
} from '@/lib/vault/vaultModuleRegistry'
import { normalizeVaultModulesFromSectionData } from '@/lib/vault/normalizeVaultModules'

const prisma = new PrismaClient()

function asRecord(x: unknown): Record<string, unknown> | null {
  if (x && typeof x === 'object' && !Array.isArray(x)) return x as Record<string, unknown>
  return null
}

async function main() {
  const rows = await prisma.sectionContent.findMany({
    where: {
      status: ContentStatus.PUBLISHED,
      section: {
        key: VAULT_SECTION_KEY,
        page: { template: VAULT_BUILDER_TEMPLATE },
      },
    },
    include: {
      section: {
        include: {
          page: { select: { id: true, slug: true, template: true, urlPath: true } },
        },
      },
    },
  })

  const byType = new Map<string, number>()
  const byPageSlug = new Map<string, { types: Set<string>; warningCount: number }>()
  const allWarnings: string[] = []
  let totalModules = 0
  let rowsMissingModules = 0
  let adminOnlyNoWebRenderer = 0

  for (const row of rows) {
    const slug = row.section.page.slug
    const data = row.data
    const root = asRecord(data)
    if (!root || !Array.isArray(root.modules)) {
      rowsMissingModules++
      allWarnings.push(`${slug}: data.modules absent ou non-tableau`)
      continue
    }

    const { modules, warnings } = normalizeVaultModulesFromSectionData(data, slug)
    for (const w of warnings) {
      allWarnings.push(w)
    }

    const entry = byPageSlug.get(slug) ?? { types: new Set<string>(), warningCount: 0 }
    entry.warningCount += warnings.length
    for (const m of modules) {
      totalModules++
      byType.set(m.type, (byType.get(m.type) ?? 0) + 1)
      entry.types.add(m.type)
      if (
        isAdminRegisteredVaultModuleType(m.type) &&
        !hasWebExplicitRenderer(m.type)
      ) {
        adminOnlyNoWebRenderer++
      }
    }
    byPageSlug.set(slug, entry)
  }

  const pagesWithFallbackModules = [...byPageSlug.entries()].filter(([_, v]) =>
    [...v.types].some(
      (t) => isAdminRegisteredVaultModuleType(t) && !hasWebExplicitRenderer(t),
    ),
  )

  const report = {
    generatedAt: new Date().toISOString(),
    sectionKey: VAULT_SECTION_KEY,
    template: VAULT_BUILDER_TEMPLATE,
    publishedSectionContentsScanned: rows.length,
    uniqueVaultPages: byPageSlug.size,
    totalModules,
    rowsMissingModulesArray: rowsMissingModules,
    modulesWithAdminCatalogButNoWebExplicitBranch: adminOnlyNoWebRenderer,
    byModuleType: Object.fromEntries([...byType.entries()].sort((a, b) => a[0].localeCompare(b[0]))),
    pagesWithAtLeastOneAdminOnlyModule: pagesWithFallbackModules.map(([slug]) => slug),
    warningCount: allWarnings.length,
    warningsSample: allWarnings.slice(0, 200),
  }

  console.log(JSON.stringify(report, null, 2))

  if (allWarnings.length > 200) {
    console.error(
      JSON.stringify({
        note: `${allWarnings.length - 200} warnings supplémentaires non affichés (voir warningCount)`,
      }),
    )
  }

  console.error('\nvault-modules-dry-run : OK (read-only).')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
