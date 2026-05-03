import { NextRequest, NextResponse } from 'next/server'
import { GetObjectCommand } from '@aws-sdk/client-s3'
import { Readable } from 'node:stream'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { r2Client } from '@/lib/storage/r2-client'
import { isR2Configured, r2CredentialsNotConfiguredMessage } from '@/lib/storage/r2Env'

const bucketName =
  process.env.STORAGE_BUCKET_NAME?.trim() ||
  process.env.R2_BUCKET_NAME?.trim() ||
  'arquantix-media'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

/**
 * GET /api/admin/media/[id]/file
 * Stream fichier depuis R2 (authentifié). Utilisé pour prévisualisations admin.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return new NextResponse('Unauthorized', { status: 401 })
    }

    if (!isR2Configured()) {
      const msg = r2CredentialsNotConfiguredMessage()
      console.error('[admin/media/file]', msg)
      return new NextResponse(msg, {
        status: 503,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      })
    }

    const media = await prisma.media.findUnique({
      where: { id: params.id },
    })

    if (!media) {
      return new NextResponse('Not found', { status: 404 })
    }

    const command = new GetObjectCommand({
      Bucket: bucketName,
      Key: media.key,
    })

    const result = await r2Client.send(command)

    if (!result.Body) {
      return new NextResponse('Empty object', { status: 404 })
    }

    const nodeStream = result.Body as Readable
    const webStream = Readable.toWeb(nodeStream)

    return new NextResponse(webStream as unknown as BodyInit, {
      headers: {
        'Content-Type': media.mimeType || 'application/octet-stream',
        'Cache-Control': 'private, max-age=120',
      },
    })
  } catch (error) {
    console.error('[admin/media/file] Error:', error)
    return new NextResponse('Failed to fetch media', { status: 500 })
  }
}
