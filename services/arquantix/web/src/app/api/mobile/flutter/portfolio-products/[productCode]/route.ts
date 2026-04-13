import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { prisma } from '@/lib/prisma'
import { getPresignedUrl } from '@/lib/storage/storageClient'

async function resolveMediaUrl(mediaId: string | null | undefined): Promise<string | null> {
  if (!mediaId) return null
  const media = await prisma.media.findUnique({ where: { id: mediaId } })
  if (!media) return null
  try {
    return await getPresignedUrl(media.key, 3600)
  } catch {
    return media.url
  }
}

/**
 * Si l'identifiant ressemble à un UUID (produit FastAPI), résout le product_code
 * en appelant le détail produit du Portfolio Engine.
 */
async function resolveProductCode(identifier: string): Promise<string> {
  if (!identifier.includes('-')) return identifier
  try {
    const res = await fetch(
      buildBackendUrl(`/api/portfolio-engine/products/${identifier}/detail`),
      { signal: AbortSignal.timeout(5000), cache: 'no-store' },
    )
    if (!res.ok) return identifier
    const data = (await res.json()) as Record<string, unknown>
    const code = (data.product_code ?? '').toString().trim()
    return code || identifier
  } catch {
    return identifier
  }
}

/**
 * GET /api/mobile/flutter/portfolio-products/[productCode]
 *
 * Accepte un product_code OU un UUID de produit FastAPI.
 * Retourne la config dans un format compatible avec LandingPagePreviewScreen.
 *
 * Réponse : { page: {...}, vault: { headerMediaId, modules, ... } }
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ productCode: string }> | { productCode: string } },
) {
  try {
    const resolved = await Promise.resolve(params)
    const rawCode = (resolved?.productCode ?? '').trim()
    if (!rawCode) {
      return NextResponse.json({ error: 'Missing productCode' }, { status: 400 })
    }

    const productCode = await resolveProductCode(rawCode)

    const config = await prisma.portfolioProductConfig.findUnique({
      where: { productCode },
    })

    const modules = config && Array.isArray(config.modules) ? config.modules : []
    const headerMediaId = config?.headerMediaId ?? null
    const detailMediaId = config?.detailMediaId ?? null
    const [headerMediaUrl, detailMediaUrl] = await Promise.all([
      resolveMediaUrl(headerMediaId),
      resolveMediaUrl(detailMediaId),
    ])

    // Resolve media URLs inside modules (e.g. imageUrl fields)
    const resolvedModules = await Promise.all(
      (modules as Record<string, unknown>[]).map(async (m) => {
        const content = m.content as Record<string, unknown> | undefined
        if (!content) return m
        // Resolve imageUrl if it looks like a media ID (cuid format)
        if (typeof content.imageUrl === 'string' && content.imageUrl.startsWith('c')) {
          const url = await resolveMediaUrl(content.imageUrl as string)
          if (url) return { ...m, content: { ...content, imageUrl: url } }
        }
        return m
      }),
    )

    return NextResponse.json({
      page: {
        id: config?.id ?? productCode,
        slug: productCode,
        title: null,
        description: null,
        urlPath: null,
        template: 'vault_builder',
      },
      vault: {
        templateKey: 'PageSimpleNavBarTopTitlePageContent',
        headerMediaId,
        headerMediaUrl,
        detailMediaUrl,
        navbar: {
          leftIconType: 'back',
          leftRedirectType: 'back',
          leftTarget: '',
          rightAction: { icon: 'none', redirectType: 'none', target: '' },
        },
        modules: resolvedModules,
      },
    })
  } catch (error) {
    console.error('[api/mobile/flutter/portfolio-products/[productCode]]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
