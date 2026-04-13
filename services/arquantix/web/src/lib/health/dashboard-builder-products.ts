import type { PrismaClient } from '@prisma/client'

export const FLUTTER_DS_CHAPTER_SLUG = 'component_ds_flutter'
export const DASHBOARD_LAYOUT_SLUG = 'dashboard_layout'
export const OFFERS_LAYOUT_SLUG = 'offers_layout'
export const WIDGET_BUILDER_WIDGETS_CHAPTER_SLUG = 'widget_builder_widgets'
export const VAULT_MARKETING_WIDGET_SLUG = 'widget-saving-vaults-marketing-paysage'
export const CRYPTO_BUNDLES_WIDGET_SLUG = 'crypto-bundles-widget'

export type DashboardBuilderProductHealth = {
  ds_component_chapters_count: number
  ds_components_count: number
  dashboard_layout_ok: boolean
  vault_widgets_ok: boolean
  offers_widgets_ok: boolean
  bundles_widgets_ok: boolean
}

export function offersLayoutIncludesExclusiveOffers(schemaJson: unknown): boolean {
  return widgetsFromOffersLayout(schemaJson).some((w) => String(w.key ?? '') === 'exclusive_offers')
}

function widgetsFromOffersLayout(schemaJson: unknown): Array<Record<string, unknown>> {
  if (schemaJson == null || typeof schemaJson !== 'object' || Array.isArray(schemaJson)) return []
  const structure = (schemaJson as Record<string, unknown>).structure
  if (structure == null || typeof structure !== 'object' || Array.isArray(structure)) return []
  const body = (structure as Record<string, unknown>).body
  if (body == null || typeof body !== 'object' || Array.isArray(body)) return []
  const widgets = (body as Record<string, unknown>).widgets
  if (!Array.isArray(widgets)) return []
  return widgets.filter((w): w is Record<string, unknown> => w != null && typeof w === 'object')
}

/**
 * Signaux produit pour layouts Flutter / widget builder (utilisé par GET /api/health/products).
 */
export async function getDashboardBuilderProductHealth(
  prisma: PrismaClient
): Promise<DashboardBuilderProductHealth> {
  const [ds_component_chapters_count, ds_components_count, flutterChapter, widgetsChapter] =
    await Promise.all([
      prisma.dsComponentChapter.count(),
      prisma.dsComponent.count(),
      prisma.dsComponentChapter.findUnique({
        where: { slug: FLUTTER_DS_CHAPTER_SLUG },
        select: { id: true },
      }),
      prisma.dsComponentChapter.findUnique({
        where: { slug: WIDGET_BUILDER_WIDGETS_CHAPTER_SLUG },
        select: { id: true },
      }),
    ])

  const flutterId = flutterChapter?.id
  const widgetsId = widgetsChapter?.id

  const [dashboardLayout, offersLayout, vaultWidget, bundlesWidget] = await Promise.all([
    flutterId
      ? prisma.dsComponent.findUnique({
          where: {
            chapterId_slug: { chapterId: flutterId, slug: DASHBOARD_LAYOUT_SLUG },
          },
          select: { id: true },
        })
      : Promise.resolve(null),
    flutterId
      ? prisma.dsComponent.findUnique({
          where: {
            chapterId_slug: { chapterId: flutterId, slug: OFFERS_LAYOUT_SLUG },
          },
          select: { id: true, schemaJson: true },
        })
      : Promise.resolve(null),
    widgetsId
      ? prisma.dsComponent.findUnique({
          where: {
            chapterId_slug: { chapterId: widgetsId, slug: VAULT_MARKETING_WIDGET_SLUG },
          },
          select: { id: true },
        })
      : Promise.resolve(null),
    widgetsId
      ? prisma.dsComponent.findUnique({
          where: {
            chapterId_slug: { chapterId: widgetsId, slug: CRYPTO_BUNDLES_WIDGET_SLUG },
          },
          select: { id: true },
        })
      : Promise.resolve(null),
  ])

  const offersHasExclusive = offersLayout
    ? offersLayoutIncludesExclusiveOffers(offersLayout.schemaJson)
    : false

  return {
    ds_component_chapters_count,
    ds_components_count,
    dashboard_layout_ok: Boolean(flutterChapter && dashboardLayout),
    vault_widgets_ok: Boolean(widgetsChapter && vaultWidget),
    offers_widgets_ok: Boolean(offersLayout && offersHasExclusive),
    bundles_widgets_ok: Boolean(widgetsChapter && bundlesWidget),
  }
}
