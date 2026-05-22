import { z } from 'zod'

/** Panneau support sticky (colonne droite portail / FAQ aside). */
export const portalSupportLocaleBlockSchema = z.object({
  title: z.string().optional(),
  description: z.string().optional(),
  ctaLabel: z.string().optional(),
  ctaHref: z.string().optional(),
  secondaryLinkLabel: z.string().optional(),
  secondaryLinkHref: z.string().optional(),
})

export const portalSupportJsonV2Schema = z.object({
  version: z.literal(2),
  defaultLocale: z.enum(['fr', 'en', 'it']),
  locales: z.object({
    fr: portalSupportLocaleBlockSchema.optional(),
    en: portalSupportLocaleBlockSchema.optional(),
    it: portalSupportLocaleBlockSchema.optional(),
  }),
})

export type PortalSupportLocaleBlock = z.infer<typeof portalSupportLocaleBlockSchema>
export type PortalSupportJsonV2 = z.infer<typeof portalSupportJsonV2Schema>
