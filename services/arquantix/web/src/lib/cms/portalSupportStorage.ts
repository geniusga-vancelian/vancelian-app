import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'
import {
  portalSupportJsonV2Schema,
  portalSupportLocaleBlockSchema,
  type PortalSupportJsonV2,
  type PortalSupportLocaleBlock,
} from '@/lib/cms/portalSupportSchema'

export type AdminPortalSupportLoadPayload = {
  formatVersion: 2
  defaultLocale: Locale
  locales: Record<Locale, PortalSupportLocaleBlock>
}

export type ParsedPortalSupportStorage =
  | { kind: 'v2'; doc: PortalSupportJsonV2 }
  | { kind: 'invalid' }

export function parsePortalSupportStorage(raw: unknown): ParsedPortalSupportStorage {
  if (raw === null || raw === undefined || typeof raw !== 'object') {
    return { kind: 'invalid' }
  }
  if ((raw as { version?: unknown }).version === 2) {
    const parsed = portalSupportJsonV2Schema.safeParse(raw)
    if (parsed.success) return { kind: 'v2', doc: parsed.data }
    return { kind: 'invalid' }
  }
  return { kind: 'invalid' }
}

export function resolvePortalSupportBlockForLocale(
  parsed: ParsedPortalSupportStorage,
  requestedLocale: Locale,
): PortalSupportLocaleBlock {
  if (parsed.kind === 'invalid') return {}

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
    if (block !== undefined) return block
  }
  return {}
}

const emptyLocalesRecord = (): Record<Locale, PortalSupportLocaleBlock> => ({
  fr: {},
  en: {},
  it: {},
})

export function getAdminPortalSupportLoadPayload(raw: unknown): AdminPortalSupportLoadPayload {
  const parsed = parsePortalSupportStorage(raw ?? {})
  if (parsed.kind === 'v2') {
    const doc = parsed.doc
    return {
      formatVersion: 2,
      defaultLocale: doc.defaultLocale,
      locales: {
        fr: doc.locales.fr ?? {},
        en: doc.locales.en ?? {},
        it: doc.locales.it ?? {},
      },
    }
  }
  return {
    formatVersion: 2,
    defaultLocale: 'fr',
    locales: emptyLocalesRecord(),
  }
}

export function basePortalSupportV2DocForMerge(
  parsed: ParsedPortalSupportStorage,
): PortalSupportJsonV2 {
  if (parsed.kind === 'v2') return parsed.doc
  return portalSupportJsonV2Schema.parse({
    version: 2,
    defaultLocale: 'fr',
    locales: { fr: {}, en: {}, it: {} },
  })
}

export function buildPortalSupportJsonV2AfterLocaleEdit(input: {
  existingRaw: unknown
  locale: Locale
  defaultLocale: Locale
  block: PortalSupportLocaleBlock
}): PortalSupportJsonV2 {
  const parsed = parsePortalSupportStorage(input.existingRaw ?? {})
  const base = basePortalSupportV2DocForMerge(parsed)
  const block = portalSupportLocaleBlockSchema.parse(input.block)
  return portalSupportJsonV2Schema.parse({
    version: 2,
    defaultLocale: input.defaultLocale,
    locales: {
      fr: input.locale === 'fr' ? block : (base.locales.fr ?? {}),
      en: input.locale === 'en' ? block : (base.locales.en ?? {}),
      it: input.locale === 'it' ? block : (base.locales.it ?? {}),
    },
  })
}
