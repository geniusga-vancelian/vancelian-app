/**
 * Cloudflare R2 Storage Client Configuration
 *
 * Uses AWS S3 SDK v3 (compatible with R2)
 * Endpoint: R2_ENDPOINT or STORAGE_ENDPOINT (https://<account-id>.r2.cloudflarestorage.com)
 */

import { S3Client } from '@aws-sdk/client-s3'
import { getR2AccessKeyId, getR2Endpoint, getR2SecretAccessKey } from './r2Env'

const endpoint = getR2Endpoint()
const accessKeyId = getR2AccessKeyId()
const secretAccessKey = getR2SecretAccessKey()

if (!endpoint || !accessKeyId || !secretAccessKey) {
  console.warn(
    '⚠️  R2 / STORAGE credentials not configured. Media uploads will fail. ' +
    'Set R2_* or STORAGE_* (endpoint, access key id, secret).'
  )
}

/**
 * S3Client configured for Cloudflare R2
 */
export const r2Client = new S3Client({
  region: 'auto', // R2 doesn't require a specific region
  endpoint: endpoint || undefined,
  credentials: accessKeyId && secretAccessKey
    ? {
        accessKeyId,
        secretAccessKey,
      }
    : undefined,
})

