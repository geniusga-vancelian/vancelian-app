import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'
import {
  footerJsonV2Schema,
  footerSchema,
  type FooterJsonInput,
  type FooterJsonV2,
} from '@/lib/sections/library'

/** Réponse normalisée pour l’admin (édition multilingue). */
export type AdminFooterLoadPayload = {
  formatVersion: 1 | 2
  /** `true` si le stockage DB est encore l’objet plat legacy (sera migré en v2 à la sauvegarde). */
  isLegacyStorage: boolean
  defaultLocale: Locale
  locales: Record<Locale, FooterJsonInput>
}

export type ParsedFooterStorage =
  | { kind: 'legacy'; data: FooterJsonInput }
  | { kind: 'v2'; doc: FooterJsonV2 }
  | { kind: 'invalid' }

/**
 * Détecte et parse `footer_json` : legacy (plat) ou v2 (`version: 2`).
 */
export function parseFooterStorage(raw: unknown): ParsedFooterStorage {
  if (raw === null || raw === undefined || typeof raw !== 'object') {
    return { kind: 'invalid' }
  }
  if ((raw as { version?: unknown }).version === 2) {
    const p = footerJsonV2Schema.safeParse(raw)
    if (p.success) return { kind: 'v2', doc: p.data }
    return { kind: 'invalid' }
  }
  const legacy = footerSchema.safeParse(raw)
  if (legacy.success) return { kind: 'legacy', data: legacy.data }
  return { kind: 'invalid' }
}

/**
 * Chaîne de fallback pour le runtime : locale demandée → defaultLocale du doc → fr → autres clés.
 * Legacy : même contenu quelle que soit la locale.
 */
export function resolveFooterPayloadForLocale(
  parsed: ParsedFooterStorage,
  requestedLocale: Locale,
): FooterJsonInput {
  if (parsed.kind === 'invalid') return {}
  if (parsed.kind === 'legacy') return parsed.data

  const doc = parsed.doc
  const map = doc.locales
  const order: Locale[] = [
    requestedLocale,
    doc.defaultLocale,
    defaultLocale,
    ...supportedLocales.filter(
      (l) => l !== requestedLocale && l !== doc.defaultLocale && l !== defaultLocale,
    ),
  ]
  const seen = new Set<Locale>()
  for (const loc of order) {
    if (seen.has(loc)) continue
    seen.add(loc)
    const block = map[loc]
    if (block !== undefined) {
      return block
    }
  }
  return {}
}

export function isFooterJsonV2Raw(raw: unknown): raw is Record<string, unknown> & { version: 2 } {
  return typeof raw === 'object' && raw !== null && (raw as { version?: unknown }).version === 2
}

const emptyLocalesRecord = (): Record<Locale, FooterJsonInput> => ({
  fr: {},
  en: {},
  it: {},
})

/**
 * Données footer pour le formulaire admin : toujours trois blocs `fr` / `en` / `it`.
 * Legacy : tout le contenu est exposé dans `locales.fr` (comportement Lot 4).
 */
export function getAdminFooterLoadPayload(raw: unknown): AdminFooterLoadPayload {
  const parsed = parseFooterStorage(raw ?? {})
  if (parsed.kind === 'v2') {
    const doc = parsed.doc
    return {
      formatVersion: 2,
      isLegacyStorage: false,
      defaultLocale: doc.defaultLocale,
      locales: {
        fr: doc.locales.fr ?? {},
        en: doc.locales.en ?? {},
        it: doc.locales.it ?? {},
      },
    }
  }
  if (parsed.kind === 'legacy') {
    return {
      formatVersion: 1,
      isLegacyStorage: true,
      defaultLocale: 'fr',
      locales: {
        fr: parsed.data,
        en: {},
        it: {},
      },
    }
  }
  return {
    formatVersion: 1,
    isLegacyStorage: false,
    defaultLocale: 'fr',
    locales: emptyLocalesRecord(),
  }
}

/**
 * Base v2 utilisée pour fusionner une langue sans perdre les autres.
 * Legacy → contenu unique placé dans `locales.fr` (aligné chargement admin).
 */
export function baseFooterV2DocForMerge(parsed: ParsedFooterStorage): FooterJsonV2 {
  if (parsed.kind === 'v2') return parsed.doc
  if (parsed.kind === 'legacy') {
    return footerJsonV2Schema.parse({
      version: 2,
      defaultLocale: 'fr',
      locales: { fr: parsed.data, en: {}, it: {} },
    })
  }
  return footerJsonV2Schema.parse({
    version: 2,
    defaultLocale: 'fr',
    locales: { fr: {}, en: {}, it: {} },
  })
}

/**
 * Écrit un document v2 complet : remplace uniquement `locale` par `block`, conserve le reste.
 * `defaultLocale` du document = secours runtime (éditable dans l’admin).
 */
export function buildFooterJsonV2AfterLocaleEdit(input: {
  existingRaw: unknown
  locale: Locale
  defaultLocale: Locale
  block: FooterJsonInput
}): FooterJsonV2 {
  const parsed = parseFooterStorage(input.existingRaw ?? {})
  const base = baseFooterV2DocForMerge(parsed)
  return footerJsonV2Schema.parse({
    version: 2,
    defaultLocale: input.defaultLocale,
    locales: {
      fr: input.locale === 'fr' ? input.block : (base.locales.fr ?? {}),
      en: input.locale === 'en' ? input.block : (base.locales.en ?? {}),
      it: input.locale === 'it' ? input.block : (base.locales.it ?? {}),
    },
  })
}
