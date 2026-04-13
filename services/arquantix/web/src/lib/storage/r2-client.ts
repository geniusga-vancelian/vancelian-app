/**
 * Cloudflare R2 Storage Client Configuration
 * 
 * Uses AWS S3 SDK v3 (compatible with R2)
 * Endpoint: R2_ENDPOINT (format: https://<account-id>.r2.cloudflarestorage.com)
 */

import { S3Client } from '@aws-sdk/client-s3'

const endpoint = process.env.R2_ENDPOINT
const accessKeyId = process.env.R2_ACCESS_KEY_ID
const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY

if (!endpoint || !accessKeyId || !secretAccessKey) {
  console.warn(
    '⚠️  R2 credentials not configured. Media uploads will fail. ' +
    'Set R2_ENDPOINT, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY in your environment.'
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

