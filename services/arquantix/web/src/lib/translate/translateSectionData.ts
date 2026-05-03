import type { TranslationOptions } from './types'
import { translateText } from './translateText'
import { translateMarkdown } from './translateMarkdown'
import {
  getStringAtLot1Path,
  setStringAtLot1Path,
} from '@/lib/i18n/integrity/fieldPathAccess'
import { expandTranslatablePaths } from '@/lib/i18n/translatablePathExpansion'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import { resolveSectionI18nPolicy } from '@/lib/sections/sectionI18nPolicy'

/**
 * Traduit le JSON `data` d'une section CMS vers la `targetLocale`.
 *
 * Source de vérité unique pour les chemins traduisibles :
 * `SECTION_I18N_POLICIES` (`@/lib/sections/sectionI18nPolicy`).
 *
 * Expansion des chemins dynamiques (`items[]`, `tags[]`, `cards[].buttons[]`…)
 * via `@/lib/i18n/translatablePathExpansion` — **même** moteur que
 * `pageCheckLanguage` pour garantir que tout champ scanné par « Vérifier la
 * langue » est aussi traduisible par l'auto-traduction (et inversement).
 */

function isMarkdownPath(
  path: string,
  canonicalKey: string | null,
): boolean {
  const lower = path.toLowerCase()
  if (lower.includes('markdown')) return true
  if (canonicalKey === 'cta' && /(^|\.)description$/.test(path)) return true
  if (canonicalKey === 'company_map' && /(^|\.)bodyContent$/i.test(path)) return true
  return false
}

export async function translateSectionData(
  data: any,
  sectionKey: string,
  options: TranslationOptions,
): Promise<any> {
  const canonicalKey = resolveCanonicalSectionKey(sectionKey)
  const resolved = resolveSectionI18nPolicy(sectionKey, canonicalKey)

  if (resolved.kind === 'notTranslatable') {
    return data
  }

  if (resolved.kind === 'missingPolicy') {
    if (process.env.NODE_ENV !== 'production') {
      console.warn(
        `[translateSectionData] Aucune politique i18n pour la section "${sectionKey}" — ajouter une entrée dans sectionI18nPolicy.ts`,
      )
    }
    return data
  }

  const translated =
    typeof structuredClone !== 'undefined'
      ? structuredClone(data)
      : JSON.parse(JSON.stringify(data))

  for (const abstractPath of resolved.paths) {
    const concretePaths = expandTranslatablePaths(translated, abstractPath)
    for (const concretePath of concretePaths) {
      // `getStringAtLot1Path` / `setStringAtLot1Path` accepent un chemin
      // préfixé `data.` pour le domaine `cms_section` (préfixe stripé en
      // interne). On respecte la convention pour rester homogène avec
      // `pageCheckLanguage` et tracer plus facilement.
      const lookupPath = `data.${concretePath}`
      const value = getStringAtLot1Path(translated, 'cms_section', lookupPath)
      if (typeof value !== 'string' || !value.trim()) continue

      try {
        const useMarkdown = isMarkdownPath(concretePath, canonicalKey)
        const result = useMarkdown
          ? await translateMarkdown(value, options)
          : await translateText(value, options)
        setStringAtLot1Path(translated, 'cms_section', lookupPath, result.translated)
      } catch (error) {
        console.error(`Error translating ${concretePath}:`, error)
      }
    }
  }

  return translated
}
