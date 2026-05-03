/**
 * Orchestration migration Projects → Vault + PackagedProduct + lien lending.
 * Appelé par scripts/migrate-exclusive-offers-to-vault.ts
 */
import type { PrismaClient } from '@prisma/client'
import { ContentStatus, PackagedEngineType, PackagedProductType, PackagedVisibility } from '@prisma/client'

import {
  buildLandingConfig,
  buildVaultModulesFromProject,
  mapProjectStatusToCommercial,
} from './exclusiveOfferProjectMapping'

const VAULT_TEMPLATE = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'
const LOCALE = 'fr'

export type MigrationFilter = 'lending-linked' | 'has-i18n' | 'all'

export type MigrationReportEntry = {
  project_id: string
  project_slug: string
  packaged_product_id: string | null
  page_id: string | null
  lending_pool_product_id: string | null
  status: 'migrated' | 'skipped' | 'conflict' | 'error'
  reason: string
  project_media_count?: number
  notes?: string[]
}

export type MigrationResult = {
  entries: MigrationReportEntry[]
  summary: {
    migrated: number
    skipped: number
    conflicts: number
    errors: number
  }
}

export type MigrationOptions = {
  dryRun: boolean
  projectId?: string
  filter: MigrationFilter
}

function summarize(entries: MigrationReportEntry['status'][]): MigrationResult['summary'] {
  return {
    migrated: entries.filter((s) => s === 'migrated').length,
    skipped: entries.filter((s) => s === 'skipped').length,
    conflicts: entries.filter((s) => s === 'conflict').length,
    errors: entries.filter((s) => s === 'error').length,
  }
}

async function resolveInvestmentTypeSlug(
  prisma: PrismaClient,
  investmentCategoryLabel: string | null
): Promise<string | undefined> {
  if (!investmentCategoryLabel?.trim()) return undefined
  const cat = await prisma.investmentCategory.findFirst({
    where: { label: { equals: investmentCategoryLabel.trim(), mode: 'insensitive' } },
    select: { slug: true },
  })
  return cat?.slug
}

async function listProjectIds(prisma: PrismaClient, filter: MigrationFilter): Promise<string[]> {
  if (filter === 'lending-linked') {
    const rows = await prisma.lendingPoolProducts.findMany({
      where: { projectId: { not: null } },
      select: { projectId: true },
    })
    const ids = [...new Set(rows.map((r) => r.projectId).filter(Boolean))] as string[]
    return ids
  }
  if (filter === 'has-i18n') {
    const rows = await prisma.projectI18n.findMany({ select: { projectId: true }, distinct: ['projectId'] })
    return rows.map((r) => r.projectId)
  }
  const all = await prisma.project.findMany({ select: { id: true } })
  return all.map((p) => p.id)
}

async function loadProjectBundle(prisma: PrismaClient, projectId: string) {
  return prisma.project.findUnique({
    where: { id: projectId },
    include: {
      i18n: true,
      projectMedia: { orderBy: { order: 'asc' }, select: { id: true, mediaId: true, order: true } },
    },
  })
}

function pickI18n(project: NonNullable<Awaited<ReturnType<typeof loadProjectBundle>>>) {
  const fr = project.i18n.find((x) => x.locale === LOCALE)
  return fr ?? project.i18n[0] ?? null
}

export async function runExclusiveOfferMigration(
  prisma: PrismaClient,
  opts: MigrationOptions
): Promise<MigrationResult> {
  const entries: MigrationReportEntry[] = []
  let projectIds: string[] = []

  if (opts.projectId) {
    projectIds = [opts.projectId]
  } else {
    projectIds = await listProjectIds(prisma, opts.filter)
  }

  for (const pid of projectIds) {
    try {
      const row = await migrateOneProject(prisma, pid, opts.dryRun)
      entries.push(row)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      entries.push({
        project_id: pid,
        project_slug: '?',
        packaged_product_id: null,
        page_id: null,
        lending_pool_product_id: null,
        status: 'error',
        reason: msg,
      })
    }
  }

  const statuses = entries.map((e) => e.status)
  return {
    entries,
    summary: summarize(statuses),
  }
}

async function migrateOneProject(
  prisma: PrismaClient,
  projectId: string,
  dryRun: boolean
): Promise<MigrationReportEntry> {
  const notes: string[] = []
  const project = await loadProjectBundle(prisma, projectId)
  if (!project) {
    return {
      project_id: projectId,
      project_slug: '?',
      packaged_product_id: null,
      page_id: null,
      lending_pool_product_id: null,
      status: 'error',
      reason: 'PROJECT_NOT_FOUND',
    }
  }

  const i18n = pickI18n(project)
  if (!i18n) {
    return {
      project_id: project.id,
      project_slug: project.slug,
      packaged_product_id: null,
      page_id: null,
      lending_pool_product_id: null,
      status: 'conflict',
      reason: 'NO_I18N',
      notes: ['Ajouter au moins une locale project_i18n avant migration.'],
    }
  }

  const lpps = await prisma.lendingPoolProducts.findMany({
    where: { projectId: project.id },
  })

  if (lpps.length > 1) {
    return {
      project_id: project.id,
      project_slug: project.slug,
      packaged_product_id: null,
      page_id: null,
      lending_pool_product_id: null,
      status: 'conflict',
      reason: 'MULTIPLE_LENDING_PRODUCTS',
      notes: [`${lpps.length} lending_pool_products pour ce project_id (attendu: 0 ou 1).`],
    }
  }

  const lpp = lpps[0] ?? null

  const existingPackaged = await prisma.packagedProduct.findFirst({
    where: { legacyProjectId: project.id },
    include: { page: true },
  })

  if (existingPackaged) {
    const pageOk = existingPackaged.page.template === VAULT_TEMPLATE
    if (!pageOk) {
      return {
        project_id: project.id,
        project_slug: project.slug,
        packaged_product_id: existingPackaged.id,
        page_id: existingPackaged.pageId,
        lending_pool_product_id: lpp?.id ?? null,
        status: 'conflict',
        reason: 'PACKAGED_PAGE_INCOHERENT',
      }
    }

    if (lpp) {
      const linkOk =
        lpp.packagedProductId === existingPackaged.id &&
        existingPackaged.engineType === PackagedEngineType.LENDING &&
        existingPackaged.engineReferenceId === lpp.id
      if (!linkOk && !dryRun) {
        await prisma.$transaction([
          prisma.lendingPoolProducts.update({
            where: { id: lpp.id },
            data: {
              packagedProductId: existingPackaged.id,
            },
          }),
          prisma.packagedProduct.update({
            where: { id: existingPackaged.id },
            data: {
              engineType: PackagedEngineType.LENDING,
              engineReferenceId: lpp.id,
            },
          }),
        ])
        notes.push('Lien lending réaligné (était partiellement incohérent).')
      }
    }

    return {
      project_id: project.id,
      project_slug: project.slug,
      packaged_product_id: existingPackaged.id,
      page_id: existingPackaged.pageId,
      lending_pool_product_id: lpp?.id ?? null,
      status: 'skipped',
      reason: 'ALREADY_MIGRATED',
      notes: notes.length ? notes : ['legacy_project_id déjà présent — pas de réécriture contenu.'],
      project_media_count: project.projectMedia.length,
    }
  }

  const slugTaken = await prisma.packagedProduct.findFirst({
    where: {
      slug: project.slug,
      NOT: { legacyProjectId: project.id },
    },
    select: { id: true, legacyProjectId: true },
  })
  if (slugTaken) {
    return {
      project_id: project.id,
      project_slug: project.slug,
      packaged_product_id: null,
      page_id: null,
      lending_pool_product_id: lpp?.id ?? null,
      status: 'conflict',
      reason: 'SLUG_PACKAGED_TAKEN',
      notes: [`packaged_products.slug=${project.slug} déjà utilisé par ${slugTaken.id}.`],
    }
  }

  const pageBySlug = await prisma.page.findFirst({
    where: { slug: project.slug },
  })
  if (pageBySlug && pageBySlug.template !== VAULT_TEMPLATE) {
    return {
      project_id: project.id,
      project_slug: project.slug,
      packaged_product_id: null,
      page_id: pageBySlug.id,
      lending_pool_product_id: lpp?.id ?? null,
      status: 'conflict',
      reason: 'PAGE_SLUG_NON_VAULT',
      notes: [`Page ${pageBySlug.id} existe avec template=${pageBySlug.template}.`],
    }
  }

  const invSlug = await resolveInvestmentTypeSlug(prisma, project.investmentCategory)
  if (project.investmentCategory && !invSlug) {
    notes.push(
      `investmentCategory="${project.investmentCategory}" : aucun investment_categories.slug résolu (ignoré).`
    )
  }

  const modules = buildVaultModulesFromProject({
    projectId: project.id,
    title: i18n.title,
    shortDescription: i18n.shortDescription,
    description: i18n.description,
    competitiveAdvantages: i18n.competitiveAdvantages,
    howItWorks: i18n.howItWorks,
    keyInformation: i18n.keyInformation,
    faq: i18n.faq,
  })

  const headerMediaId = project.heroMediaId ?? project.coverMediaId ?? null
  if (project.projectMedia.length > 0) {
    notes.push(
      `Galerie project_media (${project.projectMedia.length} entrées) non portée vers carrousel automatiquement.`
    )
  }

  const config = buildLandingConfig({
    projectId: project.id,
    pageTitleText: i18n.title,
    headerMediaId,
    investmentTypeSlug: invSlug,
    modules,
  })

  if (dryRun) {
    const pageCandidate = pageBySlug?.id
    if (pageCandidate) {
      const clash = await prisma.packagedProduct.findFirst({
        where: { pageId: pageCandidate, NOT: { legacyProjectId: project.id } },
        select: { id: true },
      })
      if (clash) {
        return {
          project_id: project.id,
          project_slug: project.slug,
          packaged_product_id: null,
          page_id: pageCandidate,
          lending_pool_product_id: lpp?.id ?? null,
          status: 'conflict',
          reason: 'PAGE_ALREADY_HAS_PACKAGED',
          notes: [...notes, `page_id=${pageCandidate} a déjà packaged ${clash.id}.`],
          project_media_count: project.projectMedia.length,
        }
      }
    }
    return {
      project_id: project.id,
      project_slug: project.slug,
      packaged_product_id: null,
      page_id: pageCandidate ?? null,
      lending_pool_product_id: lpp?.id ?? null,
      status: 'migrated',
      reason: 'DRY_RUN_OK',
      notes: [...notes, 'dry-run: aucune écriture.'],
      project_media_count: project.projectMedia.length,
    }
  }

  let pageId = pageBySlug?.id

  if (!pageId) {
    const urlPath =
      project.slug === 'home' ? '/' : `/projects/${project.slug}`
    const created = await prisma.page.create({
      data: {
        slug: project.slug,
        urlPath,
        title: i18n.title,
        description: i18n.shortDescription ?? null,
        template: VAULT_TEMPLATE,
        sections: {
          create: {
            key: VAULT_SECTION_KEY,
            order: 0,
            schemaVersion: 'v1',
            contents: {
              create: [
                {
                  locale: LOCALE,
                  status: ContentStatus.DRAFT,
                  data: config as object,
                  updatedByUserId: null,
                },
                {
                  locale: LOCALE,
                  status: ContentStatus.PUBLISHED,
                  data: config as object,
                  updatedByUserId: null,
                },
              ],
            },
          },
        },
      },
    })
    pageId = created.id
  } else {
    const section = await prisma.section.findUnique({
      where: { pageId_key: { pageId, key: VAULT_SECTION_KEY } },
    })
    if (!section) {
      return {
        project_id: project.id,
        project_slug: project.slug,
        packaged_product_id: null,
        page_id: pageId,
        lending_pool_product_id: lpp?.id ?? null,
        status: 'conflict',
        reason: 'VAULT_PAGE_WITHOUT_SECTION',
      }
    }
    for (const st of [ContentStatus.DRAFT, ContentStatus.PUBLISHED]) {
      await prisma.sectionContent.upsert({
        where: {
          sectionId_locale_status: {
            sectionId: section.id,
            locale: LOCALE,
            status: st,
          },
        },
        update: { data: config as object },
        create: {
          sectionId: section.id,
          locale: LOCALE,
          status: st,
          data: config as object,
          updatedByUserId: null,
        },
      })
    }
    await prisma.page.update({
      where: { id: pageId },
      data: {
        title: i18n.title,
        description: i18n.shortDescription ?? null,
      },
    })
  }

  const otherOnPage = await prisma.packagedProduct.findFirst({
    where: {
      pageId: pageId!,
      NOT: { legacyProjectId: project.id },
    },
    select: { id: true },
  })
  if (otherOnPage) {
    return {
      project_id: project.id,
      project_slug: project.slug,
      packaged_product_id: null,
      page_id: pageId,
      lending_pool_product_id: lpp?.id ?? null,
      status: 'conflict',
      reason: 'PAGE_ALREADY_HAS_PACKAGED',
      notes: [`page_id=${pageId} a déjà packaged_product ${otherOnPage.id}.`],
    }
  }

  const commercial = mapProjectStatusToCommercial(project.status)

  const packaged = await prisma.packagedProduct.create({
    data: {
      slug: project.slug,
      pageId: pageId!,
      productType: PackagedProductType.EXCLUSIVE_OFFER,
      commercialStatus: commercial,
      visibility: PackagedVisibility.PUBLIC,
      featuredRank: null,
      categorySlug: null,
      legacyProjectId: project.id,
      publishedAt: commercial === 'PUBLISHED' ? new Date() : null,
    },
  })

  if (lpp) {
    if (lpp.packagedProductId && lpp.packagedProductId !== packaged.id) {
      return {
        project_id: project.id,
        project_slug: project.slug,
        packaged_product_id: packaged.id,
        page_id: pageId,
        lending_pool_product_id: lpp.id,
        status: 'conflict',
        reason: 'LENDING_LINKED_OTHER_PACKAGED',
      }
    }
    await prisma.$transaction([
      prisma.lendingPoolProducts.update({
        where: { id: lpp.id },
        data: { packagedProductId: packaged.id },
      }),
      prisma.packagedProduct.update({
        where: { id: packaged.id },
        data: {
          engineType: PackagedEngineType.LENDING,
          engineReferenceId: lpp.id,
        },
      }),
    ])
  }

  return {
    project_id: project.id,
    project_slug: project.slug,
    packaged_product_id: packaged.id,
    page_id: pageId!,
    lending_pool_product_id: lpp?.id ?? null,
    status: 'migrated',
    reason: lpp ? 'MIGRATED_WITH_LENDING' : 'MIGRATED_NO_LENDING',
    notes,
    project_media_count: project.projectMedia.length,
  }
}
