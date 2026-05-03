/**
 * Détection prudente : `franc` restreint à fra/eng/ita, seuils explicites.
 * Petits textes → NEEDS_REVIEW. Mélange → heuristique par segments.
 */

import { franc, francAll } from 'franc'

import type { Locale } from '@/config/locales'
import { isValidLocale } from '@/config/locales'

import type { LinguisticAuditStatus } from '@/lib/i18n/integrity/types'
import { prepareTextForLanguageDetection } from '@/lib/i18n/integrity/textPrep'

const FRANC_ONLY = ['fra', 'eng', 'ita'] as const

/** ISO 639-3 → locale site. */
function iso3ToLocale(code: string): Locale | undefined {
  if (code === 'fra') return 'fr'
  if (code === 'eng') return 'en'
  if (code === 'ita') return 'it'
  return undefined
}

/** Texte trop court pour trigrammes fiables (franc minLength par défaut = 10 ; on est plus strict). */
const MIN_CHARS_REVIEW = 24

/** Au-dessus : détection acceptée si non `und`. */
const MIN_CHARS_DETECT = 25

const MIXED_MIN_SEGMENT = 20

function confidenceFromFrancDistance(distance: number): number {
  // Distances trigrammes : typiquement 0–plusieurs centaines ; plus bas = meilleur match.
  const d = Math.max(0, Math.min(400, distance))
  return Math.round((1 - d / 400) * 100) / 100
}

function topFrancTuple(text: string): { iso3: string; distance: number } {
  const tuples = francAll(text, { only: [...FRANC_ONLY], minLength: MIN_CHARS_DETECT })
  const first = tuples[0]
  if (!first) return { iso3: 'und', distance: 999 }
  return { iso3: first[0], distance: typeof first[1] === 'number' ? first[1] : 200 }
}

/**
 * Détecte mélange FR/EN/IT sur segments (phrases / paragraphes).
 */
function detectMixedLocales(prepared: string): Set<Locale> | null {
  const parts = prepared
    .split(/\n{2,}|(?<=[.!?])\s+/)
    .map((p) => p.trim())
    .filter((p) => p.length >= MIXED_MIN_SEGMENT)

  if (parts.length < 2) return null

  const set = new Set<Locale>()
  for (const p of parts.slice(0, 12)) {
    const code = franc(p, { only: [...FRANC_ONLY], minLength: MIXED_MIN_SEGMENT })
    const loc = iso3ToLocale(code)
    if (loc) set.add(loc)
    if (set.size >= 2) break
  }
  return set.size >= 2 ? set : null
}

export type ClassifyTextResult = {
  status: LinguisticAuditStatus
  detectedIso6393: string
  detectedLocale?: Locale
  confidence: number
  suggestedAction?: string
}

/**
 * Classifie un champ texte par rapport à `targetLocale`.
 * - Chaîne vide / manquante : à gérer par l’appelant (MISSING).
 */
export function classifyTextForTargetLocale(
  rawText: string | undefined | null,
  targetLocale: Locale,
): ClassifyTextResult {
  if (rawText == null || (typeof rawText === 'string' && rawText.trim() === '')) {
    return {
      status: 'MISSING',
      detectedIso6393: 'und',
      confidence: 0,
      suggestedAction: 'Renseigner le contenu pour cette locale (brouillon).',
    }
  }

  const prepared = prepareTextForLanguageDetection(rawText)
  if (prepared.length < MIN_CHARS_REVIEW) {
    return {
      status: 'NEEDS_REVIEW',
      detectedIso6393: 'und',
      confidence: 0.35,
      suggestedAction:
        'Texte trop court pour une détection fiable — vérification manuelle recommandée.',
    }
  }

  const mixed = detectMixedLocales(prepared)
  if (mixed && mixed.size >= 2) {
    return {
      status: 'MIXED_LANGUAGE',
      detectedIso6393: 'mul',
      confidence: 0.55,
      suggestedAction: 'Plusieurs langues détectées dans le même champ — découper ou traduire manuellement.',
    }
  }

  if (prepared.length < MIN_CHARS_DETECT) {
    return {
      status: 'NEEDS_REVIEW',
      detectedIso6393: 'und',
      confidence: 0.45,
      suggestedAction: 'Texte court — confirmer la langue à la main.',
    }
  }

  const { iso3, distance } = topFrancTuple(prepared)
  const conf = confidenceFromFrancDistance(distance)

  if (iso3 === 'und') {
    return {
      status: 'NEEDS_REVIEW',
      detectedIso6393: 'und',
      confidence: 0.4,
      suggestedAction: 'Langue indéterminée (franc) — revue manuelle.',
    }
  }

  const loc = iso3ToLocale(iso3)
  if (!loc) {
    return {
      status: 'NEEDS_REVIEW',
      detectedIso6393: iso3,
      confidence: conf,
      suggestedAction: 'Langue hors périmètre fra/eng/ita — revue manuelle.',
    }
  }

  if (loc === targetLocale) {
    return {
      status: 'OK',
      detectedIso6393: iso3,
      detectedLocale: loc,
      confidence: conf,
    }
  }

  return {
    status: 'WRONG_LANGUAGE',
    detectedIso6393: iso3,
    detectedLocale: loc,
    confidence: conf,
    suggestedAction: `La langue détectée (${loc}) ne correspond pas à la locale cible (${targetLocale}).`,
  }
}

export function assertValidTargetLocale(locale: string): locale is Locale {
  return isValidLocale(locale)
}
