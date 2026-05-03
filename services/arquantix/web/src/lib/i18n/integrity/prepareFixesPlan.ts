/**
 * Lot 2 — plan de correctifs : lecture Prisma uniquement, aucune mutation.
 */

import { ContentStatus } from '@prisma/client'

import type { Locale } from '@/config/locales'
import { isValidLocale } from '@/config/locales'

import { VAULT_SECTION_KEY } from '@/lib/catalog/packagedCatalogHelpers'
import { prisma } from '@/lib/prisma'

import { buildCorrectionProposal } from '@/lib/i18n/integrity/prepareFixesStrategies'
import { runLot1LinguisticAudit } from '@/lib/i18n/integrity/runLot1Scan'
import {
  MockTranslationProvider,
  type TranslationProvider,
} from '@/lib/i18n/integrity/translationProvider'
import type {
  CorrectionStrategy,
  LinguisticAuditFinding,
  PrepareFixesReport,
} from '@/lib/i18n/integrity/types'

function emptyStrategySummary(): Record<CorrectionStrategy, number> {
  return {
    'copy-as-is': 0,
    'translate-from-source': 0,
    'needs-review': 0,
    skip: 0,
  }
}

async function loadVaultSectionIdsByPageId(pageIds: string[]): Promise<Map<string, string>> {
  if (pageIds.length === 0) return new Map()
  const rows = await prisma.section.findMany({
    where: { pageId: { in: pageIds }, key: VAULT_SECTION_KEY },
    select: { id: true, pageId: true },
  })
  return new Map(rows.map((r) => [r.pageId, r.id]))
}

/**
 * sectionId → locale → data (DRAFT uniquement).
 */
async function loadDraftMapsBySectionIds(sectionIds: string[]): Promise<Map<string, Map<Locale, unknown>>> {
  const out = new Map<string, Map<Locale, unknown>>()
  if (sectionIds.length === 0) return out

  const rows = await prisma.sectionContent.findMany({
    where: { sectionId: { in: sectionIds }, status: ContentStatus.DRAFT },
    select: { sectionId: true, locale: true, data: true },
  })

  for (const r of rows) {
    if (!r.data || !isValidLocale(r.locale)) continue
    let m = out.get(r.sectionId)
    if (!m) {
      m = new Map()
      out.set(r.sectionId, m)
    }
    m.set(r.locale, r.data as unknown)
  }
  return out
}

function sectionIdForFinding(
  f: LinguisticAuditFinding,
  vaultPageToSection: Map<string, string>,
): string | undefined {
  if (f.domain === 'cms_section') return f.sectionId
  return vaultPageToSection.get(f.pageId)
}

/**
 * Audit lot 1 + propositions lot 2. Aucun write DB.
 */
export async function runPrepareFixesPlan(
  targetLocale: Locale,
  provider: TranslationProvider = new MockTranslationProvider(),
): Promise<PrepareFixesReport> {
  const audit = await runLot1LinguisticAudit(targetLocale)

  const vaultPageIds = [...new Set(audit.findings.filter((f) => f.domain === 'vault').map((f) => f.pageId))]
  const vaultPageToSection = await loadVaultSectionIdsByPageId(vaultPageIds)

  const sectionIds = new Set<string>()
  for (const f of audit.findings) {
    const sid = sectionIdForFinding(f, vaultPageToSection)
    if (sid) sectionIds.add(sid)
  }

  const draftMaps = await loadDraftMapsBySectionIds([...sectionIds])

  const proposals: PrepareFixesReport['proposals'] = []
  for (const f of audit.findings) {
    if (f.status === 'OK') continue
    const sid = sectionIdForFinding(f, vaultPageToSection)
    const byLocale = sid ? draftMaps.get(sid) : undefined
    proposals.push(await buildCorrectionProposal(f, byLocale, targetLocale, provider))
  }

  const summary = emptyStrategySummary()
  for (const p of proposals) {
    summary[p.strategy] += 1
  }

  return {
    generatedAt: new Date().toISOString(),
    lot: 2,
    targetLocale,
    contentLayer: 'DRAFT',
    auditReference: {
      generatedAt: audit.generatedAt,
      lot: 1,
      findingCount: audit.findings.length,
    },
    proposals,
    summary,
    meta: {
      readOnly: true,
      noDbWrites: true,
      scopeDescription:
        'Lot 2 : préparation de correctifs sur le périmètre lot 1 (vault + hero / hero_secondary / cta, DRAFT). Preview uniquement — aucun apply, aucune écriture SectionContent.',
    },
  }
}
