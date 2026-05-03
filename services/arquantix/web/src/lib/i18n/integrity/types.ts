/**
 * Lot 1 — audit linguistique (lecture seule). Statuts explicites, extensibles aux lots suivants.
 */

import type { Locale } from '@/config/locales'

/** Statut par champ texte allowlisté. */
export type LinguisticAuditStatus =
  | 'OK'
  | 'MISSING'
  | 'WRONG_LANGUAGE'
  | 'MIXED_LANGUAGE'
  | 'NEEDS_REVIEW'
  | 'NON_TRANSLATABLE'

export type IntegrityDomain = 'vault' | 'cms_section'

/** Une entrée de rapport (aucune écriture DB). */
export type LinguisticAuditFinding = {
  id: string
  domain: IntegrityDomain
  targetLocale: Locale
  pageSlug: string
  pageId: string
  /** Section CMS (`hero`, `cta`) ou `vault_builder_v1` pour le vault. */
  sectionKey?: string
  sectionId?: string
  /** Index du module dans `modules[]` (vault uniquement). */
  moduleIndex?: number
  moduleType?: string
  /** Chemin logique (ex. `modules[2].content.title`, `data.title`). */
  fieldPath: string
  status: LinguisticAuditStatus
  excerpt: string
  detectedIso6393?: string
  /** Langue projetée site (fr/en/it) si applicable. */
  detectedLocale?: Locale
  /** 0–1, interprétation prudente (voir `languageStatus.ts`). */
  confidence: number
  /** Message informatif uniquement (pas d’action automatique en Lot 1). */
  suggestedAction?: string
}

export type LinguisticAuditReport = {
  generatedAt: string
  lot: 1
  targetLocale: Locale
  /** Uniquement DRAFT pour la locale cible. */
  contentLayer: 'DRAFT'
  summary: {
    totalFindings: number
    byStatus: Record<LinguisticAuditStatus, number>
    vaultPagesScanned: number
    cmsSectionsScanned: number
  }
  findings: LinguisticAuditFinding[]
  meta: {
    /** Périmètre Lot 1 documenté. */
    scopeDescription: string
    /** Aucune écriture, aucune traduction. */
    readOnly: true
  }
}

/** Lot 2 — préparation de correctifs (preview uniquement, aucune écriture DB). */
export type CorrectionStrategy =
  | 'copy-as-is'
  | 'translate-from-source'
  | 'needs-review'
  | 'skip'

export type CorrectionProposal = {
  id: string
  findingId: string
  pageSlug: string
  domain: IntegrityDomain
  fieldPath: string
  auditStatus: LinguisticAuditStatus
  strategy: CorrectionStrategy
  sourceLocale?: Locale
  sourceTextExcerpt?: string
  currentText: string
  proposedText?: string
  /** 0–1 — prudence Lot 2 (mock traduction = confiance modérée). */
  confidence: number
  recommendedAction: string
  rationale: string
}

export type PrepareFixesReport = {
  generatedAt: string
  lot: 2
  targetLocale: Locale
  contentLayer: 'DRAFT'
  auditReference: {
    generatedAt: string
    lot: 1
    findingCount: number
  }
  proposals: CorrectionProposal[]
  summary: Record<CorrectionStrategy, number>
  meta: {
    readOnly: true
    noDbWrites: true
    scopeDescription: string
  }
}
