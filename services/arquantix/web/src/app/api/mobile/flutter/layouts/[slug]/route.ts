import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getPresignedUrl } from '@/lib/storage/storageClient'

const LAYOUT_SLUG_ALIAS: Record<string, string> = {
  dashboard: 'dashboard_layout',
  offers: 'offers_layout',
  'euro-account': 'euro_account_layout',
  'all-transactions': 'all_transactions_layout',
  'transaction-detail': 'transaction_detail_layout',
  'exclusive-offer-detail': 'exclusive_offer_detail_layout',
}

function resolveLayoutDbSlug(rawSlug: string): string {
  const normalized = rawSlug.trim().toLowerCase()
  if (!normalized) return ''
  return LAYOUT_SLUG_ALIAS[normalized] ?? normalized
}

function extractStorageKeyFromUrl(imageUrl: string): string | null {
  const raw = imageUrl.trim()
  if (!raw) return null

  try {
    const parsed = new URL(raw)
    const key = decodeURIComponent(parsed.pathname.replace(/^\/+/, ''))
    return key || null
  } catch {
    const key = decodeURIComponent(raw.replace(/^\/+/, ''))
    return key || null
  }
}

/**
 * GET /api/mobile/flutter/layouts/[slug]
 * API publique pour l'app Flutter: retourne un layout DS flutter par slug.
 */
export async function GET(
  _request: Request,
  { params }: { params: { slug: string } }
) {
  try {
    const requestedSlug = (params.slug ?? '').toString()
    const resolvedDbSlug = resolveLayoutDbSlug(requestedSlug)
    if (!resolvedDbSlug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

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
          slug: resolvedDbSlug,
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
      return NextResponse.json({ error: `Layout not found for slug "${requestedSlug}"` }, { status: 404 })
    }

    let layout = component.schemaJson as Record<string, any> | null

    // Si un background image est configure dans le header, regenere une URL signee fraiche.
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
          console.warn(`[api/mobile/flutter/layouts/${requestedSlug}] Failed to refresh signed image URL:`, err)
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
          requestedSlug,
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
    console.error('[api/mobile/flutter/layouts/[slug]]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
