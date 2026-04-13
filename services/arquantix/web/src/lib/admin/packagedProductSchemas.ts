/**
 * Validation Zod pour l’admin Product Registry (PackagedProduct lié aux pages Vault Builder).
 */
import {
  PackagedCommercialStatus,
  PackagedProductType,
  PackagedVisibility,
} from '@prisma/client'
import { z } from 'zod'

import { isValidSlug } from '@/lib/utils/slugify'

export const packagedProductTypeSchema = z.nativeEnum(PackagedProductType)
export const packagedCommercialStatusSchema = z.nativeEnum(PackagedCommercialStatus)
export const packagedVisibilitySchema = z.nativeEnum(PackagedVisibility)

/** Tags : tableau de chaînes non vides, longueur raisonnable. */
export const packagedTagsSchema = z
  .array(z.string().trim().min(1).max(120))
  .max(64)
  .optional()
  .default([])

/**
 * Corps PUT /api/admin/packaged-products/by-page/[pageId]
 * — enabled=false supprime l’entrée si elle existe (sauf liaison lending).
 */
export const packagedProductByPagePutSchema = z
  .object({
    enabled: z.boolean(),
    slug: z.string().optional(),
    productType: packagedProductTypeSchema.optional(),
    commercialStatus: packagedCommercialStatusSchema.optional(),
    visibility: packagedVisibilitySchema.optional(),
    featuredRank: z.union([z.number().int().min(0).max(1_000_000), z.null()]).optional(),
    categorySlug: z
      .string()
      .trim()
      .max(200)
      .optional()
      .nullable(),
    tags: packagedTagsSchema,
  })
  .superRefine((data, ctx) => {
    if (!data.enabled) return
    const slug = data.slug?.trim() ?? ''
    if (!slug) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Le slug est requis lorsque le produit packagé est activé.',
        path: ['slug'],
      })
      return
    }
    if (!isValidSlug(slug)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Slug invalide (lettres minuscules, chiffres et tirets, max 255 caractères).',
        path: ['slug'],
      })
    }
    if (!data.productType) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Le type de produit est requis lorsque le produit packagé est activé.',
        path: ['productType'],
      })
    }
  })

export type PackagedProductByPagePutInput = z.infer<typeof packagedProductByPagePutSchema>

/** Construit le corps PUT à partir du brouillon UI (lance si champs invalides). */
export function buildPackagedPutBodyFromDraft(draft: {
  enabled: boolean
  slug: string
  productType: string
  commercialStatus: string
  visibility: string
  featuredRank: string
  categorySlug: string
  tagsText: string
}): PackagedProductByPagePutInput {
  if (!draft.enabled) {
    return packagedProductByPagePutSchema.parse({ enabled: false })
  }

  let featuredRank: number | null = null
  if (draft.featuredRank.trim() !== '') {
    const n = parseInt(draft.featuredRank, 10)
    if (!Number.isFinite(n) || n < 0 || n > 1_000_000) {
      throw new Error('Rang mis en avant invalide (entier entre 0 et 1 000 000).')
    }
    featuredRank = n
  }
  const tags = parseTagsInput(draft.tagsText)
  return packagedProductByPagePutSchema.parse({
    enabled: true,
    slug: draft.slug.trim() || undefined,
    productType: packagedProductTypeSchema.parse(draft.productType),
    commercialStatus: packagedCommercialStatusSchema.parse(draft.commercialStatus),
    visibility: packagedVisibilitySchema.parse(draft.visibility),
    featuredRank,
    categorySlug: draft.categorySlug.trim() || null,
    tags,
  })
}

/** Parse une saisie texte (virgules ou retours ligne) vers tags normalisés. */
export function parseTagsInput(raw: string): string[] {
  if (!raw.trim()) return []
  const parts = raw
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  const seen = new Set<string>()
  const out: string[] = []
  for (const p of parts) {
    if (seen.has(p)) continue
    seen.add(p)
    out.push(p)
    if (out.length >= 64) break
  }
  return out
}
