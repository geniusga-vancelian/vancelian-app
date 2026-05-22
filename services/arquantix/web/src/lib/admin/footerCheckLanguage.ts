/**
 * Adaptateur « Vérifier la langue » du footer global du site.
 *
 * Footer = `GlobalSettings.footerJson` (format v2 multilingue) — édité dans
 * `SiteFooterEditor`. Chaque locale a son bloc `FooterJsonInput` indépendant.
 *
 * Champs scannés (visibles côté site, choix « strict minimum visible ») :
 *   - `copyright`
 *   - `description`
 *   - `links[i].label`
 *   - `newsletterTitle`
 *   - `newsletterPlaceholder`
 *   - `newsletterButtonLabel`
 *   - `legalTexts[i]`
 *
 * Volontairement exclus :
 *   - `links[i].category` : clé de groupement interne, pas affichée telle
 *     quelle (sert juste à fabriquer les colonnes via `buildNavColumns`).
 *   - URLs (`href`, `socialLinks[].href`) : pas du contenu textuel.
 *   - `backgroundColor`, `logoMediaId`, `logoMediaInvert`, `companyAddress`, `secondaryNote`, `newsletterVisible` : pas du texte.
 *
 * Le module ne persiste rien : il fournit l'extraction + la projection des
 * corrections dans un nouveau bloc footer. La route API se charge ensuite
 * d'écrire via `buildFooterJsonV2AfterLocaleEdit`.
 */

import type { Locale } from '@/config/locales'

import {
  applyFieldsLanguageFixes,
  buildLanguageHintsFromGenericScan,
  scanFieldsLanguageDeep,
  type GenericApplyResult,
  type GenericFieldInput,
  type GenericScanResult,
} from '@/lib/admin/i18n/genericLanguageCheck'
import type { BatchLanguageRefiner } from '@/lib/i18n/llm/batchClassifyLanguages'
import type { FooterJsonInput } from '@/lib/sections/library'

const DOMAIN = 'footer'

/**
 * Construit la liste plate de champs à scanner pour un bloc footer locale.
 *
 * Les `hintKey` sont stables et alignés sur les chemins (`copyright`,
 * `links[3].label`, `legalTexts[1]`, …) pour permettre à l'apply de
 * re-projeter trivialement.
 */
export function extractFooterFields(block: FooterJsonInput): GenericFieldInput[] {
  const fields: GenericFieldInput[] = []

  const pushPlain = (path: string, value: unknown) => {
    if (typeof value !== 'string') return
    if (!value.trim()) return
    fields.push({
      hintKey: path,
      path,
      value,
      kind: 'plain',
      domain: DOMAIN,
    })
  }

  pushPlain('copyright', block.copyright)
  pushPlain('description', block.description)
  pushPlain('newsletterTitle', block.newsletterTitle)
  pushPlain('newsletterPlaceholder', block.newsletterPlaceholder)
  pushPlain('newsletterButtonLabel', block.newsletterButtonLabel)

  const links = Array.isArray(block.links) ? block.links : []
  links.forEach((link, idx) => {
    pushPlain(`links[${idx}].label`, link?.label)
  })

  const legalTexts = Array.isArray(block.legalTexts) ? block.legalTexts : []
  legalTexts.forEach((text, idx) => {
    pushPlain(`legalTexts[${idx}]`, text)
  })

  return fields
}

/**
 * Projette les corrections (`fixedByHintKey`) dans un nouveau bloc footer.
 *
 * Mute jamais l'entrée : retourne un nouveau bloc.
 */
export function applyFooterFixesToBlock(
  original: FooterJsonInput,
  fixedByHintKey: Map<string, string>,
): FooterJsonInput {
  if (fixedByHintKey.size === 0) return { ...original }

  const next: FooterJsonInput = { ...original }

  const get = (key: string) => fixedByHintKey.get(key)

  const copyright = get('copyright')
  if (copyright !== undefined) next.copyright = copyright

  const description = get('description')
  if (description !== undefined) next.description = description

  const newsletterTitle = get('newsletterTitle')
  if (newsletterTitle !== undefined) next.newsletterTitle = newsletterTitle

  const newsletterPlaceholder = get('newsletterPlaceholder')
  if (newsletterPlaceholder !== undefined) {
    next.newsletterPlaceholder = newsletterPlaceholder
  }

  const newsletterButtonLabel = get('newsletterButtonLabel')
  if (newsletterButtonLabel !== undefined) {
    next.newsletterButtonLabel = newsletterButtonLabel
  }

  if (Array.isArray(original.links) && original.links.length > 0) {
    next.links = original.links.map((link, idx) => {
      const newLabel = get(`links[${idx}].label`)
      if (newLabel === undefined) return link
      return { ...link, label: newLabel }
    })
  }

  if (Array.isArray(original.legalTexts) && original.legalTexts.length > 0) {
    next.legalTexts = original.legalTexts.map((text, idx) => {
      const newText = get(`legalTexts[${idx}]`)
      return newText !== undefined ? newText : text
    })
  }

  return next
}

/**
 * Scan deep d'un bloc footer pour la `targetLocale`.
 *
 * Fin enveloppe autour de `scanFieldsLanguageDeep` qui injecte
 * `extractFooterFields`.
 */
export async function scanFooterLanguageDeep(
  block: FooterJsonInput,
  targetLocale: Locale,
  options?: { refiner?: BatchLanguageRefiner },
): Promise<GenericScanResult> {
  const fields = extractFooterFields(block)
  return scanFieldsLanguageDeep(fields, targetLocale, options)
}

/**
 * Apply complet : scan deep → hints → traduction → projection dans un
 * nouveau bloc footer (sans persistence).
 *
 * Retourne :
 *   - `patchedBlock` : nouveau bloc à persister via la route admin.
 *   - `apply` : diagnostic de l'apply (champs corrigés + skippés + tokens).
 *   - `scan` : le scan deep utilisé pour fabriquer les hints (exposé pour
 *     traçabilité dans la modale UI).
 */
export async function applyFooterLanguageFixes(
  block: FooterJsonInput,
  targetLocale: Locale,
  options?: {
    refiner?: BatchLanguageRefiner
    /** Permet d'injecter un scan deep déjà calculé pour éviter un 2e LLM. */
    scan?: GenericScanResult
  },
): Promise<{
  patchedBlock: FooterJsonInput
  apply: GenericApplyResult
  scan: GenericScanResult
}> {
  const fields = extractFooterFields(block)
  const scan = options?.scan ?? (await scanFieldsLanguageDeep(fields, targetLocale, options))
  const languageHints = buildLanguageHintsFromGenericScan(scan)
  const apply = await applyFieldsLanguageFixes(fields, targetLocale, { languageHints })
  const patchedBlock = applyFooterFixesToBlock(block, apply.fixedByHintKey)
  return { patchedBlock, apply, scan }
}
