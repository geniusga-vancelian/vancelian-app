import { ContentStatus } from '@prisma/client'
import type { Locale } from '@/config/locales'
import { defaultLocale, supportedLocales } from '@/config/locales'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogConstants'

/**
 * Niveau éditorial par locale (Lot 6) — basé sur SectionContent PUBLISHED + titres PageI18n.
 * Pas d’heuristique sur le JSON des sections : on compte les blocs publiés vs nombre de sections.
 */
export type LocaleCompletenessLevel = 'complete' | 'partial' | 'missing' | 'no_sections'

export type PageLocaleCompleteness = {
  locales: Record<Locale, LocaleCompletenessLevel>
}

export type PageCompletenessInput = {
  id: string
  template: string
  title: string | null
  description: string | null
  pageI18n: Array<{ locale: string; title: string | null; description: string | null }>
  sections: Array<{
    id: string
    contents: Array<{ locale: string; status: string }>
  }>
}

export type I18nSiteSummary = {
  /** Pages avec au moins une section (base des compteurs manquant/partiel). */
  pagesWithSections: number
  pagesNoSections: number
  missingEn: number
  missingIt: number
  partialEn: number
  partialIt: number
  /** Vault builder : sous-ensemble des pages « missing » pour EN / IT. */
  vaultMissingEn: number
  vaultMissingIt: number
}

function nonEmptyTitle(s: string | null | undefined): boolean {
  return typeof s === 'string' && s.trim().length > 0
}

function hasTitleForLocale(
  locale: Locale,
  baseTitle: string | null,
  pageI18n: PageCompletenessInput['pageI18n'],
): boolean {
  const row = pageI18n.find((r) => r.locale === locale)
  if (locale === defaultLocale) {
    return nonEmptyTitle(row?.title) || nonEmptyTitle(baseTitle)
  }
  return nonEmptyTitle(row?.title)
}

/** Métadonnées SEO : on exige au moins titre OU description renseignée pour EN/IT si pas de titre pageI18n. */
function hasSeoSignalForLocale(
  locale: Locale,
  baseTitle: string | null,
  baseDescription: string | null,
  pageI18n: PageCompletenessInput['pageI18n'],
): boolean {
  if (hasTitleForLocale(locale, baseTitle, pageI18n)) return true
  const row = pageI18n.find((r) => r.locale === locale)
  if (locale === defaultLocale) {
    return nonEmptyTitle(row?.description) || nonEmptyTitle(baseDescription)
  }
  return nonEmptyTitle(row?.description)
}

function levelForLocale(
  locale: Locale,
  input: PageCompletenessInput,
): LocaleCompletenessLevel {
  const sectionCount = input.sections.length
  if (sectionCount === 0) return 'no_sections'

  let publishedCount = 0
  let draftAny = false

  for (const sec of input.sections) {
    const byLoc = sec.contents.filter((c) => c.locale === locale)
    const hasPub = byLoc.some((c) => c.status === 'PUBLISHED')
    const hasDraft = byLoc.some((c) => c.status === 'DRAFT')
    if (hasPub) publishedCount++
    if (hasDraft && !hasPub) draftAny = true
  }

  const seoOk = hasSeoSignalForLocale(
    locale,
    input.title,
    input.description,
    input.pageI18n,
  )

  if (publishedCount === 0 && !draftAny) return 'missing'
  if (publishedCount === 0 && draftAny) return 'partial'
  if (publishedCount < sectionCount) return 'partial'
  if (publishedCount === sectionCount && !seoOk) return 'partial'
  return 'complete'
}

/**
 * Pastilles par langue pour une section seule : PUBLISHED → complet, DRAFT seul → partiel, rien → absent.
 */
export function computeSectionContentLocaleCompleteness(section: {
  contents: Array<{ locale: string; status: string }>
}): Record<Locale, LocaleCompletenessLevel> {
  const out = {} as Record<Locale, LocaleCompletenessLevel>
  for (const loc of supportedLocales) {
    const byLoc = section.contents.filter((c) => c.locale === loc)
    const hasPub = byLoc.some((c) => c.status === 'PUBLISHED')
    const hasDraft = byLoc.some((c) => c.status === 'DRAFT')
    if (hasPub) out[loc] = 'complete'
    else if (hasDraft) out[loc] = 'partial'
    else out[loc] = 'missing'
  }
  return out
}

export function computePageLocaleCompleteness(
  input: PageCompletenessInput,
): PageLocaleCompleteness {
  const locales = {} as Record<Locale, LocaleCompletenessLevel>
  for (const loc of supportedLocales) {
    locales[loc] = levelForLocale(loc, input)
  }
  return { locales }
}

/** Complétude par locale pour un article blog (table `articles` + `article_i18n`). */
export function computeArticleLocaleCompleteness(article: {
  status: ContentStatus
  i18n: Array<{ locale: string; title: string; standfirst: string }>
}): Record<Locale, LocaleCompletenessLevel> {
  const out = {} as Record<Locale, LocaleCompletenessLevel>
  const published = article.status === ContentStatus.PUBLISHED
  for (const loc of supportedLocales) {
    const row = article.i18n.find((r) => r.locale === loc)
    if (!row) {
      out[loc] = 'missing'
      continue
    }
    // Le standfirst est désormais optionnel : seul le titre conditionne
    // qu'une locale soit considérée comme renseignée.
    const textOk = row.title.trim().length > 0
    if (!textOk) {
      out[loc] = 'missing'
      continue
    }
    out[loc] = published ? 'complete' : 'partial'
  }
  return out
}

export function aggregateI18nSiteSummary(
  pages: PageCompletenessInput[],
): I18nSiteSummary {
  const summary: I18nSiteSummary = {
    pagesWithSections: 0,
    pagesNoSections: 0,
    missingEn: 0,
    missingIt: 0,
    partialEn: 0,
    partialIt: 0,
    vaultMissingEn: 0,
    vaultMissingIt: 0,
  }

  for (const p of pages) {
    const { locales } = computePageLocaleCompleteness(p)
    const isVault = p.template === VAULT_BUILDER_TEMPLATE

    if (locales.fr === 'no_sections' && locales.en === 'no_sections' && locales.it === 'no_sections') {
      summary.pagesNoSections++
      continue
    }
    summary.pagesWithSections++

    if (locales.en === 'missing') {
      summary.missingEn++
      if (isVault) summary.vaultMissingEn++
    } else if (locales.en === 'partial') {
      summary.partialEn++
    }

    if (locales.it === 'missing') {
      summary.missingIt++
      if (isVault) summary.vaultMissingIt++
    } else if (locales.it === 'partial') {
      summary.partialIt++
    }
  }

  return summary
}

export function localeCompletenessLabel(level: LocaleCompletenessLevel): string {
  switch (level) {
    case 'complete':
      return 'Complet (publié + SEO mini)'
    case 'partial':
      return 'Partiel ou brouillon'
    case 'missing':
      return 'Absent'
    case 'no_sections':
      return 'Sans sections'
    default:
      return level
  }
}

/** Ligne MenuItemI18n pour complétude des libellés (boutons zone droite). */
export type MenuItemI18nCompletenessRow = {
  locale: string
  label: string
  translationStatus: string
}

function navButtonLabelNonEmpty(s: string | null | undefined): boolean {
  return typeof s === 'string' && s.trim().length > 0
}

/**
 * Complétude i18n pour une collection Help (`help_collection_i18n`) :
 * titre vide ou ligne absente → absent ; MACHINE → partiel ; ORIGINAL / APPROVED → complet.
 */
export function computeHelpCollectionLocaleCompleteness(collection: {
  i18n?: Array<{
    locale: string
    title: string
    translationStatus: string
  }>
}): Record<Locale, LocaleCompletenessLevel> {
  const out = {} as Record<Locale, LocaleCompletenessLevel>
  for (const loc of supportedLocales) {
    const row = collection.i18n?.find((r) => r.locale === loc)
    const titleOk = typeof row?.title === 'string' && row.title.trim().length > 0
    if (!row || !titleOk) {
      out[loc] = 'missing'
      continue
    }
    if (row.translationStatus === 'MACHINE') {
      out[loc] = 'partial'
      continue
    }
    out[loc] = 'complete'
  }
  return out
}

/**
 * Pastilles FR / EN / IT pour un bouton d’action menu : libellé de base (`MenuItem.label`)
 * + `menu_item_i18n` (statut MACHINE → partiel).
 */
export function computeNavActionButtonLabelCompleteness(
  baseLabel: string,
  i18nRows: MenuItemI18nCompletenessRow[],
): Record<Locale, LocaleCompletenessLevel> {
  const out = {} as Record<Locale, LocaleCompletenessLevel>
  for (const loc of supportedLocales) {
    const row = i18nRows.find((r) => r.locale === loc)
    if (loc === defaultLocale) {
      const has = navButtonLabelNonEmpty(row?.label) || navButtonLabelNonEmpty(baseLabel)
      if (!has) {
        out[loc] = 'missing'
        continue
      }
      out[loc] = row?.translationStatus === 'MACHINE' ? 'partial' : 'complete'
      continue
    }
    if (!navButtonLabelNonEmpty(row?.label)) {
      out[loc] = 'missing'
      continue
    }
    out[loc] = row?.translationStatus === 'MACHINE' ? 'partial' : 'complete'
  }
  return out
}
