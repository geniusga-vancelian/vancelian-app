/**
 * Storage Client — couche applicative pour upload / delete / URL publique / présignature.
 *
 * Backend agnostique : AWS S3 (prod via `STORAGE_*`) ou Cloudflare R2 (dev local via `R2_*`).
 */

import { PutObjectCommand, DeleteObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'
import { r2Client } from './r2-client'
import { assertR2Configured, isR2Backend } from './r2Env'

const bucketName =
  process.env.STORAGE_BUCKET_NAME?.trim() ||
  process.env.R2_BUCKET_NAME?.trim() ||
  'arquantix-media'

const publicUrl =
  process.env.STORAGE_PUBLIC_URL?.trim() || process.env.R2_PUBLIC_URL?.trim() || ''

const endpoint =
  process.env.STORAGE_ENDPOINT?.trim() || process.env.R2_ENDPOINT?.trim() || ''

const region =
  process.env.STORAGE_REGION?.trim() || process.env.AWS_REGION?.trim() || 'us-east-1'

export interface UploadResult {
  key: string
  url: string
  size: number
  contentType: string
}

/**
 * Upload a file to the storage bucket (S3 or R2).
 */
export async function uploadFile(
  file: Buffer,
  key: string,
  contentType: string
): Promise<UploadResult> {
  assertR2Configured()

  const command = new PutObjectCommand({
    Bucket: bucketName,
    Key: key,
    Body: file,
    ContentType: contentType,
  })

  await r2Client.send(command)

  const url = getPublicUrl(key)

  return {
    key,
    url,
    size: file.length,
    contentType,
  }
}

/**
 * Delete a file from the storage bucket.
 */
export async function deleteFile(key: string): Promise<void> {
  assertR2Configured()

  const command = new DeleteObjectCommand({
    Bucket: bucketName,
    Key: key,
  })

  await r2Client.send(command)
}

/**
 * Best-effort public URL for a given object key.
 *
 * Order :
 *  1. `STORAGE_PUBLIC_URL` / `R2_PUBLIC_URL` (CDN, custom domain, ou bucket URL S3 explicite).
 *  2. Si endpoint = R2 : `https://pub-<account>.r2.dev/<key>`.
 *  3. Si endpoint = S3 natif : `https://<bucket>.s3.<region>.amazonaws.com/<key>`.
 *  4. Sinon throw.
 *
 * Note : avec un bucket S3 privé, ces URLs *ne sont pas accessibles publiquement* — c'est
 * normal. Le frontend doit alors utiliser le proxy `/api/site/media/[id]` ou une présignature.
 */
export function getPublicUrl(key: string): string {
  if (publicUrl) {
    const baseUrl = publicUrl.replace(/\/$/, '')
    return `${baseUrl}/${key}`
  }

  if (isR2Backend() && endpoint) {
    const match = endpoint.match(/https:\/\/([^.]+)\.r2\.cloudflarestorage\.com/)
    if (match && match[1]) {
      return `https://pub-${match[1]}.r2.dev/${key}`
    }
  }

  // AWS S3 natif : virtual-hosted style URL régional. Si le bucket est privé, l'URL servira
  // pour la présignature ; un GET direct retournera 403 sans signature, ce qui est attendu.
  if (!isR2Backend() && bucketName) {
    return `https://${bucketName}.s3.${region}.amazonaws.com/${key}`
  }

  throw new Error('Storage endpoint not configured (set STORAGE_PUBLIC_URL or STORAGE_ENDPOINT)')
}

/**
 * Generate a presigned URL for private access.
 */
export async function getPresignedUrl(key: string, expiresIn: number = 3600): Promise<string> {
  assertR2Configured()

  const command = new GetObjectCommand({
    Bucket: bucketName,
    Key: key,
  })

  return getSignedUrl(r2Client, command, { expiresIn })
}
