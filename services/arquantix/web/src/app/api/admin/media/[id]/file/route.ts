import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { streamMediaByRecord } from '@/lib/storage/streamMediaFile'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

/**
 * GET /api/admin/media/[id]/file
 * Stream fichier média (authentifié). R2 ou repli `public/` pour URLs locales.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return new NextResponse('Unauthorized', { status: 401 })
    }

    const media = await prisma.media.findUnique({
      where: { id: params.id },
    })

    if (!media) {
      return new NextResponse('Not found', { status: 404 })
    }

    const streamed = await streamMediaByRecord(media, {
      cacheControl: 'private, max-age=120',
    })
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
    console.error('[admin/media/file] Error:', error)
    return new NextResponse('Failed to fetch media', { status: 500 })
  }
}
