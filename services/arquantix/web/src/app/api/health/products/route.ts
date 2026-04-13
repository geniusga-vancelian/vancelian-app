import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'

import { formatDatabaseUrlTarget } from '@/lib/db/diagnostics'
import { getDashboardBuilderProductHealth } from '@/lib/health/dashboard-builder-products'
import { prisma } from '@/lib/prisma'

export const dynamic = 'force-dynamic'

/**
 * GET /api/health/products
 * Smoke checks for CMS + catalogue data used by mobile / marketing surfaces.
 */
export async function GET() {
  try {
    const [categories, bundles, vaultPages, blogPublished, builder] = await Promise.all([
      prisma.investmentCategory.count(),
      prisma.bundles.count(),
      prisma.page.count({ where: { template: 'vault_builder' } }),
      prisma.article.count({ where: { status: ContentStatus.PUBLISHED } }),
      getDashboardBuilderProductHealth(prisma),
    ])

    return NextResponse.json({
      categories,
      bundles,
      blog_count: blogPublished,
      vault_config: vaultPages > 0 ? 'ok' : 'ko',
      ds_component_chapters_count: builder.ds_component_chapters_count,
      ds_components_count: builder.ds_components_count,
      dashboard_layout_ok: builder.dashboard_layout_ok,
      vault_widgets_ok: builder.vault_widgets_ok,
      offers_widgets_ok: builder.offers_widgets_ok,
      bundles_widgets_ok: builder.bundles_widgets_ok,
      db: formatDatabaseUrlTarget(process.env.DATABASE_URL),
    })
  } catch (e) {
    console.error('[health/products]', formatDatabaseUrlTarget(process.env.DATABASE_URL), e)
    return NextResponse.json(
      {
        error: 'health_check_failed',
        categories: -1,
        bundles: -1,
        blog_count: -1,
        vault_config: 'ko',
        ds_component_chapters_count: -1,
        ds_components_count: -1,
        dashboard_layout_ok: false,
        vault_widgets_ok: false,
        offers_widgets_ok: false,
        bundles_widgets_ok: false,
        db: formatDatabaseUrlTarget(process.env.DATABASE_URL),
      },
      { status: 503 }
    )
  }
}
