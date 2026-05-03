import { z } from 'zod'
import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'
import { getSectionType } from '@/lib/sections/library'
import {
  deepMerge,
  deepMergeThree,
  mergeCommonModuleResolvedData,
  pickTranslatableFromData,
  resolveCommonModuleDesignLayer,
  stripTranslatableFromData,
} from '@/lib/cms/commonModuleDesignSplit'

const localeBlockSchema = z.record(z.string(), z.any()).optional()

export const commonModuleEntryStoredSchema = z.object({
  id: z.string().uuid(),
  label: z.string().min(1).max(200),
  sectionKey: z.string().min(1),
  defaultLocale: z.enum(['fr', 'en', 'it']),
  /** Médias, couleurs, opacités, options d’affichage — communs à toutes les langues. */
  design: z.record(z.string(), z.any()).optional(),
  locales: z.object({
    fr: localeBlockSchema,
    en: localeBlockSchema,
    it: localeBlockSchema,
  }),
})

export type CommonModuleEntryStored = z.infer<typeof commonModuleEntryStoredSchema>

export const commonModulesDocumentSchema = z.object({
  version: z.literal(1),
  modules: z.array(commonModuleEntryStoredSchema),
})

export type CommonModulesDocument = z.infer<typeof commonModulesDocumentSchema>

export function parseCommonModulesDocument(raw: unknown): CommonModulesDocument {
  const p = commonModulesDocumentSchema.safeParse(raw)
  if (p.success) return p.data
  return { version: 1, modules: [] }
}

export function getCommonModuleById(
  doc: CommonModulesDocument,
  id: string,
): CommonModuleEntryStored | undefined {
  return doc.modules.find((m) => m.id === id)
}

/**
 * Normalise : `design` explicite + `locales` réduites aux champs traduisibles.
 */
export function normalizeCommonModuleEntry(entry: CommonModuleEntryStored): CommonModuleEntryStored {
  const type = getSectionType(entry.sectionKey)
  const base = (type?.defaultData ?? {}) as Record<string, unknown>
  const design = resolveCommonModuleDesignLayer(entry, base)

  const locales = {} as Record<Locale, Record<string, unknown>>
  for (const loc of supportedLocales) {
    const raw = (entry.locales[loc] ?? {}) as Record<string, unknown>
    locales[loc] = pickTranslatableFromData(deepMergeThree(base, design, raw), entry.sectionKey)
  }

  return commonModuleEntryStoredSchema.parse({ ...entry, design, locales })
}

/**
 * Données effectives pour une locale (secours : locale demandée → defaultLocale du module → `fr` → autres).
 */
export function resolveCommonModuleDataForLocale(
  entry: CommonModuleEntryStored,
  requestedLocale: Locale,
): Record<string, unknown> {
  return mergeCommonModuleResolvedData(entry, requestedLocale)
}

export function emptyCommonModulesDocument(): CommonModulesDocument {
  return { version: 1, modules: [] }
}

export function buildCommonModulesDocAfterLocaleEdit(input: {
  existingRaw: unknown
  moduleId: string
  locale: Locale
  defaultLocale: Locale
  /** Données du formulaire « texte » (peut être l’objet complet : seuls les champs traduisibles sont conservés). */
  block: Record<string, unknown>
}): CommonModulesDocument {
  const base = parseCommonModulesDocument(input.existingRaw ?? null)
  const idx = base.modules.findIndex((m) => m.id === input.moduleId)
  if (idx < 0) {
    throw new Error('Module commun introuvable')
  }
  const prev = base.modules[idx]
  const st = getSectionType(prev.sectionKey)
  if (!st) throw new Error('Type inconnu')

  const baseDef = (st.defaultData ?? {}) as Record<string, unknown>
  const design = resolveCommonModuleDesignLayer(prev, baseDef)

  const textOnly = pickTranslatableFromData(input.block, prev.sectionKey)
  const merged = deepMergeThree(baseDef, design, textOnly)
  st.zodSchema.parse(merged)

  const draft: CommonModuleEntryStored = commonModuleEntryStoredSchema.parse({
    ...prev,
    defaultLocale: input.defaultLocale,
    design,
    locales: {
      fr: input.locale === 'fr' ? textOnly : (prev.locales.fr ?? {}),
      en: input.locale === 'en' ? textOnly : (prev.locales.en ?? {}),
      it: input.locale === 'it' ? textOnly : (prev.locales.it ?? {}),
    },
  })
  const nextEntry = normalizeCommonModuleEntry(draft)
  const modules = [...base.modules]
  modules[idx] = nextEntry
  return commonModulesDocumentSchema.parse({ version: 1, modules })
}

export function buildCommonModulesDocAfterDesignEdit(input: {
  existingRaw: unknown
  moduleId: string
  /** Sortie du panneau « Apparence » (médias, couleurs…). */
  designBlock: Record<string, unknown>
}): CommonModulesDocument {
  const base = parseCommonModulesDocument(input.existingRaw ?? null)
  const idx = base.modules.findIndex((m) => m.id === input.moduleId)
  if (idx < 0) throw new Error('Module commun introuvable')
  const prev = base.modules[idx]
  const st = getSectionType(prev.sectionKey)
  if (!st) throw new Error('Type inconnu')

  const baseDef = (st.defaultData ?? {}) as Record<string, unknown>
  const designPatch = stripTranslatableFromData(input.designBlock, prev.sectionKey)
  const previousLayer = resolveCommonModuleDesignLayer(prev, baseDef)
  const newDesign = deepMerge(previousLayer, designPatch)

  const textRef = (prev.locales[prev.defaultLocale] ?? {}) as Record<string, unknown>
  const merged = deepMergeThree(baseDef, newDesign, textRef)
  st.zodSchema.parse(merged)

  const draft: CommonModuleEntryStored = commonModuleEntryStoredSchema.parse({
    ...prev,
    design: newDesign,
  })
  const nextEntry = normalizeCommonModuleEntry(draft)
  const modules = [...base.modules]
  modules[idx] = nextEntry
  return commonModulesDocumentSchema.parse({ version: 1, modules })
}

export function buildCommonModulesDocAfterLabelEdit(input: {
  existingRaw: unknown
  moduleId: string
  label: string
}): CommonModulesDocument {
  const base = parseCommonModulesDocument(input.existingRaw ?? null)
  const idx = base.modules.findIndex((m) => m.id === input.moduleId)
  if (idx < 0) throw new Error('Module commun introuvable')
  const prev = base.modules[idx]
  const modules = [...base.modules]
  modules[idx] = commonModuleEntryStoredSchema.parse({
    ...prev,
    label: input.label.trim(),
  })
  return commonModulesDocumentSchema.parse({ version: 1, modules })
}

export function buildCommonModulesDocAfterDelete(input: {
  existingRaw: unknown
  moduleId: string
}): CommonModulesDocument {
  const base = parseCommonModulesDocument(input.existingRaw ?? null)
  const modules = base.modules.filter((m) => m.id !== input.moduleId)
  return commonModulesDocumentSchema.parse({ version: 1, modules })
}

export function buildCommonModulesDocAfterCreate(input: {
  existingRaw: unknown
  id: string
  label: string
  sectionKey: string
  defaultLocale: Locale
}): CommonModulesDocument {
  const type = getSectionType(input.sectionKey)
  if (!type) throw new Error(`Type de section inconnu: ${input.sectionKey}`)
  const seed = (type.defaultData ?? {}) as Record<string, unknown>
  const base = parseCommonModulesDocument(input.existingRaw ?? null)
  const design = stripTranslatableFromData(seed, input.sectionKey)
  const text = pickTranslatableFromData(seed, input.sectionKey)
  const textClone = () => structuredClone(text) as Record<string, unknown>
  const entry: CommonModuleEntryStored = commonModuleEntryStoredSchema.parse({
    id: input.id,
    label: input.label.trim(),
    sectionKey: input.sectionKey,
    defaultLocale: input.defaultLocale,
    design,
    locales: {
      fr: textClone(),
      en: textClone(),
      it: textClone(),
    },
  })
  return commonModulesDocumentSchema.parse({
    version: 1,
    modules: [...base.modules, normalizeCommonModuleEntry(entry)],
  })
}
