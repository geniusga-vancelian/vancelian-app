import fs from 'node:fs'
import path from 'node:path'
import { GetObjectCommand } from '@aws-sdk/client-s3'
import { Readable } from 'node:stream'
import type { Media } from '@prisma/client'
import { getR2S3Client } from '@/lib/storage/r2-client'
import { getR2BucketName, isR2Configured } from '@/lib/storage/r2Env'

export type StreamMediaResult = {
  body: BodyInit
  contentType: string
  cacheControl: string
}

function isNoSuchKeyError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const e = error as { Code?: string; name?: string; $metadata?: { httpStatusCode?: number } }
  return e.Code === 'NoSuchKey' || e.name === 'NoSuchKey' || e.$metadata?.httpStatusCode === 404
}

/** Lit un fichier média depuis R2, ou depuis `public/` si l’URL stockée est locale (`/cms/...`). */
export async function streamMediaByRecord(
  media: Pick<Media, 'key' | 'url' | 'mimeType' | 'filename'>,
  options?: { cacheControl?: string },
): Promise<StreamMediaResult | null> {
  const contentType = media.mimeType || 'application/octet-stream'
  const cacheControl = options?.cacheControl ?? 'public, max-age=300, s-maxage=300'

  if (isR2Configured()) {
    try {
      const result = await getR2S3Client().send(
        new GetObjectCommand({
          Bucket: getR2BucketName(),
          Key: media.key,
        }),
      )
      if (result.Body) {
        const nodeStream = result.Body as Readable
        return {
          body: Readable.toWeb(nodeStream) as BodyInit,
          contentType,
          cacheControl,
        }
      }
    } catch (error) {
      if (!isNoSuchKeyError(error)) {
        throw error
      }
    }
  }

  const localPath = resolveLocalPublicMediaPath(media.url)
  if (localPath && fs.existsSync(localPath)) {
    const buffer = fs.readFileSync(localPath)
    return { body: buffer, contentType, cacheControl }
  }

  return null
}

/** `/cms/foo.mp4` → `{cwd}/public/cms/foo.mp4` */
export function resolveLocalPublicMediaPath(storedUrl: string): string | null {
  if (!storedUrl.startsWith('/') || storedUrl.startsWith('//')) return null
  return path.join(process.cwd(), 'public', storedUrl)
}
