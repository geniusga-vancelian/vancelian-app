import { NextResponse } from 'next/server'

import { mobileApiFailureResponse } from '@/lib/api/mobile-json-error'
import { prisma } from '@/lib/prisma'
import { getPresignedUrl } from '@/lib/storage/storageClient'

function extractStorageKeyFromUrl(imageUrl: string): string | null {
  const raw = imageUrl.trim()
  if (!raw) return null

  try {
    const parsed = new URL(raw)
    const key = decodeURIComponent(parsed.pathname.replace(/^\/+/, ''))
    return key || null
  } catch {
    // Tolere aussi un format direct "media/file.jpg"
    const key = decodeURIComponent(raw.replace(/^\/+/, ''))
    return key || null
  }
}

/**
 * GET /api/mobile/flutter/layouts/dashboard
 * API publique pour l'app Flutter: retourne le layout Dashboard stocké en base.
 */
export async function GET() {
  try {
    const chapter = await prisma.dsComponentChapter.findUnique({
      where: { slug: 'component_ds_flutter' },
      select: { id: true },
    })

    if (!chapter) {
      return NextResponse.json({ error: 'Chapter not found' }, { status: 404 })
    }

    const component = await prisma.dsComponent.findUnique({
      where: {
        chapterId_slug: {
          chapterId: chapter.id,
          slug: 'dashboard_layout',
        },
      },
      select: {
        id: true,
        slug: true,
        name: true,
        schemaJson: true,
      },
    })

    if (!component) {
      return NextResponse.json({ error: 'Dashboard layout not found' }, { status: 404 })
    }

    let layout = component.schemaJson as Record<string, any> | null

    // Si un background image est configuré, régénère une URL signée fraîche
    // (évite les liens R2 expirés stockés en base).
    const backgroundImageUrl = layout?.structure?.header?.background?.imageUrl
    if (typeof backgroundImageUrl === 'string' && backgroundImageUrl.trim().length > 0) {
      const key = extractStorageKeyFromUrl(backgroundImageUrl)
      if (key) {
        try {
          const freshSignedUrl = await getPresignedUrl(key, 3600)
          layout = JSON.parse(JSON.stringify(layout ?? {}))
          if (layout?.structure?.header?.background) {
            layout.structure.header.background.imageUrl = freshSignedUrl
          }
        } catch (err) {
          console.warn('[api/mobile/flutter/layouts/dashboard] Failed to refresh signed image URL:', err)
        }
      }
    }

    return NextResponse.json(
      {
        layout,
        meta: {
          id: component.id,
          slug: component.slug,
          name: component.name,
        },
      },
      {
        headers: {
          'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
          Pragma: 'no-cache',
          Expires: '0',
        },
      }
    )
  } catch (error) {
    return mobileApiFailureResponse('[api/mobile/flutter/layouts/dashboard]', error)
  }
}
