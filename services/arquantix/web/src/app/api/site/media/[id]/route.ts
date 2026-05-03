import { NextRequest, NextResponse } from 'next/server'
import { GetObjectCommand } from '@aws-sdk/client-s3'
import { Readable } from 'node:stream'
import { prisma } from '@/lib/prisma'
import { r2Client } from '@/lib/storage/r2-client'
import { isR2Configured, r2CredentialsNotConfiguredMessage } from '@/lib/storage/r2Env'

const bucketName = process.env.R2_BUCKET_NAME || 'arquantix-media'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

/**
 * GET /api/site/media/[id]
 * Fichier média pour les pages **publiques** (même origine que le site).
 * Contourne les URLs « publiques » R2 inaccessibles sur bucket privé et les présignatures
 * qui échouent (timeout, etc.). L’UUID est l’identifiant déjà exposé dans le HTML CMS.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    if (!isR2Configured()) {
      const msg = r2CredentialsNotConfiguredMessage()
      console.error('[site/media]', msg)
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
        'Cache-Control': 'public, max-age=300, s-maxage=300',
      },
    })
  } catch (error) {
    console.error('[site/media] Error:', error)
    return new NextResponse('Failed to fetch media', { status: 500 })
  }
}
