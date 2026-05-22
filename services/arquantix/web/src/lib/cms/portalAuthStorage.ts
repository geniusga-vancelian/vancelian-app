import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'
import {
  portalAuthJsonV2Schema,
  portalAuthLocaleBlockSchema,
  type PortalAuthJsonV2,
  type PortalAuthLocaleBlock,
} from '@/lib/cms/portalAuthSchema'

export type AdminPortalAuthLoadPayload = {
  formatVersion: 2
  defaultLocale: Locale
  resendSeconds: number
  ssoEnabled: boolean
  locales: Record<Locale, PortalAuthLocaleBlock>
}

export type ParsedPortalAuthStorage =
  | { kind: 'v2'; doc: PortalAuthJsonV2 }
  | { kind: 'invalid' }

export function parsePortalAuthStorage(raw: unknown): ParsedPortalAuthStorage {
  if (raw === null || raw === undefined || typeof raw !== 'object') {
    return { kind: 'invalid' }
  }
  if ((raw as { version?: unknown }).version === 2) {
    const parsed = portalAuthJsonV2Schema.safeParse(raw)
    if (parsed.success) return { kind: 'v2', doc: parsed.data }
    return { kind: 'invalid' }
  }
  return { kind: 'invalid' }
}

export function resolvePortalAuthBlockForLocale(
  parsed: ParsedPortalAuthStorage,
  requestedLocale: Locale,
): PortalAuthLocaleBlock {
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

const emptyLocalesRecord = (): Record<Locale, PortalAuthLocaleBlock> => ({
  fr: {},
  en: {},
  it: {},
})

export function getAdminPortalAuthLoadPayload(raw: unknown): AdminPortalAuthLoadPayload {
  const parsed = parsePortalAuthStorage(raw ?? {})
  if (parsed.kind === 'v2') {
    const doc = parsed.doc
    return {
      formatVersion: 2,
      defaultLocale: doc.defaultLocale,
      resendSeconds: doc.resendSeconds ?? 45,
      ssoEnabled: doc.ssoEnabled === true,
      locales: {
        fr: doc.locales.fr ?? {},
        en: doc.locales.en ?? {},
        it: doc.locales.it ?? {},
      },
    }
  }
  return {
    formatVersion: 2,
    defaultLocale: 'en',
    resendSeconds: 45,
    ssoEnabled: false,
    locales: emptyLocalesRecord(),
  }
}

export function basePortalAuthV2DocForMerge(parsed: ParsedPortalAuthStorage): PortalAuthJsonV2 {
  if (parsed.kind === 'v2') return parsed.doc
  return portalAuthJsonV2Schema.parse({
    version: 2,
    defaultLocale: 'en',
    resendSeconds: 45,
    ssoEnabled: false,
    locales: { fr: {}, en: {}, it: {} },
  })
}

export function buildPortalAuthJsonV2AfterLocaleEdit(input: {
  existingRaw: unknown
  locale: Locale
  defaultLocale: Locale
  resendSeconds: number
  ssoEnabled: boolean
  block: PortalAuthLocaleBlock
}): PortalAuthJsonV2 {
  const parsed = parsePortalAuthStorage(input.existingRaw ?? {})
  const base = basePortalAuthV2DocForMerge(parsed)
  const block = portalAuthLocaleBlockSchema.parse(input.block)
  return portalAuthJsonV2Schema.parse({
    version: 2,
    defaultLocale: input.defaultLocale,
    resendSeconds: input.resendSeconds,
    ssoEnabled: input.ssoEnabled,
    locales: {
      fr: input.locale === 'fr' ? block : (base.locales.fr ?? {}),
      en: input.locale === 'en' ? block : (base.locales.en ?? {}),
      it: input.locale === 'it' ? block : (base.locales.it ?? {}),
    },
  })
}
