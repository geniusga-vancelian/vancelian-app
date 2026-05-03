/**
 * Helper bas niveau partagé pour les registres de libellés UI mutualisés.
 *
 * Sert de socle commun à `vaultCommonCta` (modules vault) et `siteCommonCta`
 * (header / footer / sections du site public). Permet d'éviter de dupliquer
 * la mécanique `Record<Locale, Table>` + fallback FR + fallback clé brute.
 *
 * Les registres concrets restent séparés volontairement :
 * - cycles de vie produit différents (vault vs site public),
 * - couplage métier propre à chaque périmètre (allowlists, auto-translate, etc.),
 * - clarté du périmètre lors des audits.
 *
 * Convention :
 * - Texte spécifique à un module / une page → prop CMS traduisible.
 * - Texte générique d'UI réutilisable → registre commun (helper ci-dessous).
 */

import type { Locale } from '@/config/locales'
import { getLocaleOrDefault } from '@/config/locales'

/**
 * Construit un lookup typé `(locale, key) => string` à partir d'une table FR
 * et d'une fonction qui résout les autres locales.
 *
 * Le fallback final est :
 *   1. valeur de la locale demandée si présente,
 *   2. valeur FR (langue de référence du projet),
 *   3. clé brute (jamais d'undefined renvoyé).
 */
export function buildCommonCtaLookup<TFr extends Record<string, string>>(params: {
  fr: TFr
  /** Table par locale. La locale FR est obligatoire ; les autres optionnelles côté typage,
   * mais en pratique on remplit FR / EN / IT pour rester cohérent avec `supportedLocales`. */
  byLocale: Record<Locale, Record<keyof TFr, string>>
}): (locale: string | null | undefined, key: keyof TFr) => string {
  const { fr, byLocale } = params
  return function commonCtaLookup(
    locale: string | null | undefined,
    key: keyof TFr,
  ): string {
    const loc = getLocaleOrDefault(locale ?? undefined)
    const table = byLocale[loc]
    return table[key] ?? fr[key] ?? String(key)
  }
}
