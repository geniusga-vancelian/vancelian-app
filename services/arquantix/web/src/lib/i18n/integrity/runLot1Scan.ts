/**
 * Lot 1 — scan lecture seule : vaults + sections `hero` / `hero_secondary` / `cta`.
 */

import { ContentStatus } from '@prisma/client'

import type { Locale } from '@/config/locales'

import { VAULT_BUILDER_TEMPLATE, VAULT_SECTION_KEY } from '@/lib/catalog/packagedCatalogHelpers'
import { prisma } from '@/lib/prisma'

import { collectCtaDraftFindings, collectHeroDraftFindings } from '@/lib/i18n/integrity/auditCmsSectionDraft'
import { collectVaultDraftFindings } from '@/lib/i18n/integrity/auditVaultDraft'
import type { LinguisticAuditFinding, LinguisticAuditReport } from '@/lib/i18n/integrity/types'

const CMS_KEYS_LOT1 = ['hero', 'hero_secondary', 'cta'] as const

const EMPTY_SUMMARY = {
  OK: 0,
  MISSING: 0,
  WRONG_LANGUAGE: 0,
  MIXED_LANGUAGE: 0,
  NEEDS_REVIEW: 0,
  NON_TRANSLATABLE: 0,
}

function buildSummary(findings: LinguisticAuditFinding[]): LinguisticAuditReport['summary'] {
  const byStatus = { ...EMPTY_SUMMARY }
  for (const f of findings) {
    byStatus[f.status] = (byStatus[f.status] ?? 0) + 1
  }
  return {
    totalFindings: findings.length,
    byStatus,
    vaultPagesScanned: 0,
    cmsSectionsScanned: 0,
  }
}

/**
 * Exécute le scan Lot 1 (aucune écriture).
 */
export async function runLot1LinguisticAudit(targetLocale: Locale): Promise<LinguisticAuditReport> {
  const findings: LinguisticAuditFinding[] = []
  let vaultPagesScanned = 0
  let cmsSectionsScanned = 0

  const vaultPages = await prisma.page.findMany({
    where: { template: VAULT_BUILDER_TEMPLATE },
    select: {
      id: true,
      slug: true,
      sections: {
        where: { key: VAULT_SECTION_KEY },
        select: {
          id: true,
          contents: {
            where: {
              locale: targetLocale,
              status: ContentStatus.DRAFT,
            },
            select: { id: true, data: true },
            take: 1,
          },
        },
      },
    },
  })

  for (const page of vaultPages) {
    vaultPagesScanned++
    const draft = page.sections[0]?.contents[0]
    if (!draft?.data) continue
    findings.push(
      ...collectVaultDraftFindings(draft.data, targetLocale, page.slug, page.id),
    )
  }

  const cmsSections = await prisma.section.findMany({
    where: {
      key: { in: [...CMS_KEYS_LOT1] },
    },
    select: {
      id: true,
      key: true,
      page: { select: { id: true, slug: true } },
      contents: {
        where: {
          locale: targetLocale,
          status: ContentStatus.DRAFT,
        },
        select: { data: true },
        take: 1,
      },
    },
  })

  for (const sec of cmsSections) {
    const draft = sec.contents[0]
    if (!draft?.data || typeof draft.data !== 'object') continue
    cmsSectionsScanned++
    const data = draft.data as Record<string, unknown>
    const slug = sec.page.slug
    const pageId = sec.page.id

    if (sec.key === 'hero' || sec.key === 'hero_secondary') {
      findings.push(
        ...collectHeroDraftFindings(data, targetLocale, slug, pageId, sec.id, sec.key),
      )
    } else if (sec.key === 'cta') {
      findings.push(...collectCtaDraftFindings(data, targetLocale, slug, pageId, sec.id))
    }
  }

  const summary = buildSummary(findings)
  summary.vaultPagesScanned = vaultPagesScanned
  summary.cmsSectionsScanned = cmsSectionsScanned

  return {
    generatedAt: new Date().toISOString(),
    lot: 1,
    targetLocale,
    contentLayer: 'DRAFT',
    summary,
    findings,
    meta: {
      scopeDescription:
        'Lot 1 : SectionContent DRAFT uniquement — vault (`vault_builder_v1`) modules TitlePage, SimpleMarkdownContentModule, FaqAccordionModule + champs pageTitle/fixedBottomCta ; sections CMS `hero`, `hero_secondary`, `cta`. Pas de PageI18n, menu, footer.',
      readOnly: true,
    },
  }
}
