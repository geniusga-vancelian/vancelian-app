import { z } from 'zod'

import { normalizeVancelianDarkColor } from '@/lib/cms/parseEditorialTitle'

/** Surcharges CMS par surface topnav (clés optionnelles = repli sur tokens `--v-*`). */
export const menuThemeSurfaceOverridesSchema = z.object({
  background: z.string().trim().min(1).optional(),
  borderBottom: z.string().trim().min(1).optional(),
  linkColor: z.string().trim().min(1).optional(),
  underlineColor: z.string().trim().min(1).optional(),
  textLinkColor: z.string().trim().min(1).optional(),
  ctaBg: z.string().trim().min(1).optional(),
  ctaFg: z.string().trim().min(1).optional(),
  ctaHoverBg: z.string().trim().min(1).optional(),
})

export const menuThemeJsonSchema = z.object({
  version: z.literal(1).default(1),
  surfaces: z
    .object({
      transparent: menuThemeSurfaceOverridesSchema.optional(),
      solid: menuThemeSurfaceOverridesSchema.optional(),
      warm: menuThemeSurfaceOverridesSchema.optional(),
      dark: menuThemeSurfaceOverridesSchema.optional(),
    })
    .optional(),
})

export type MenuThemeJson = z.infer<typeof menuThemeJsonSchema>
export type MenuThemeSurfaceOverrides = z.infer<typeof menuThemeSurfaceOverridesSchema>

export function parseMenuThemeStorage(raw: unknown): MenuThemeJson {
  const parsed = menuThemeJsonSchema.safeParse(raw)
  if (!parsed.success) {
    return menuThemeJsonSchema.parse({ version: 1 })
  }
  return normalizeMenuThemeJson(parsed.data)
}

function normalizeSurfaceOverrides(
  overrides: MenuThemeSurfaceOverrides | undefined,
): MenuThemeSurfaceOverrides | undefined {
  if (!overrides) return undefined
  const next: MenuThemeSurfaceOverrides = { ...overrides }
  if (next.background) {
    next.background = normalizeVancelianDarkColor(next.background)
  }
  return next
}

export function normalizeMenuThemeJson(theme: MenuThemeJson): MenuThemeJson {
  if (!theme.surfaces) return theme
  return {
    ...theme,
    surfaces: {
      transparent: normalizeSurfaceOverrides(theme.surfaces.transparent),
      solid: normalizeSurfaceOverrides(theme.surfaces.solid),
      warm: normalizeSurfaceOverrides(theme.surfaces.warm),
      dark: normalizeSurfaceOverrides(theme.surfaces.dark),
    },
  }
}

export function menuThemeJsonToInput(theme: MenuThemeJson): MenuThemeJson {
  return normalizeMenuThemeJson(menuThemeJsonSchema.parse(theme))
}
