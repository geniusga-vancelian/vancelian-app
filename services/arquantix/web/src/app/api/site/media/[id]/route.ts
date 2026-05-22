import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { streamMediaByRecord } from '@/lib/storage/streamMediaFile'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

/**
 * GET /api/site/media/[id]
 * Fichier média pour les pages **publiques** (même origine que le site).
 * Sert depuis R2 ou, en repli, depuis `public/` pour les URLs locales (`/cms/...`).
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const media = await prisma.media.findUnique({
      where: { id: params.id },
    })

    if (!media) {
      return new NextResponse('Not found', { status: 404 })
    }

    const streamed = await streamMediaByRecord(media)
    if (!streamed) {
      return new NextResponse('Not found', { status: 404 })
    }

    return new NextResponse(streamed.body, {
      headers: {
        'Content-Type': streamed.contentType,
        'Cache-Control': streamed.cacheControl,
        'Accept-Ranges': 'bytes',
      },
    })
  } catch (error) {
    console.error('[site/media] Error:', error)
    return new NextResponse('Failed to fetch media', { status: 500 })
  }
}
