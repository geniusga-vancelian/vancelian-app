/**
 * Fournisseur de traduction abstrait — Lot 2 : mock explicite, prêt pour un provider réel (lot 3+).
 */

import type { Locale } from '@/config/locales'

export interface TranslationProvider {
  /** Traduction ou placeholder — ne doit jamais écrire en base. */
  translate(text: string, from: Locale, to: Locale): Promise<string>
}

/**
 * Aperçu uniquement : préfixe visible pour éviter toute confusion avec une vraie traduction.
 */
export class MockTranslationProvider implements TranslationProvider {
  async translate(text: string, from: Locale, to: Locale): Promise<string> {
    if (from === to) return text
    return `[i18n-preview ${from}→${to}] ${text}`
  }
}
