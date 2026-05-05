/**
 * S3-compatible storage client (Cloudflare R2 ou AWS S3).
 * Le client est créé à la demande pour lire `process.env` au runtime (ECS Secrets),
 * pas au chargement du bundle Next au build.
 */

import { S3Client } from '@aws-sdk/client-s3'
import {
  getR2AccessKeyId,
  getR2Endpoint,
  getR2SecretAccessKey,
  getS3ClientRegion,
  isR2CloudflareEndpoint,
} from './r2Env'

let cached: { key: string; client: S3Client } | null = null

function cacheKey(): string {
  return [
    getR2Endpoint() ?? '',
    getR2AccessKeyId() ?? '',
    getR2SecretAccessKey() ?? '',
    getS3ClientRegion(),
  ].join('\0')
}

function shouldForcePathStyle(endpoint: string | undefined): boolean | undefined {
  if (!endpoint) return undefined
  if (isR2CloudflareEndpoint()) return true
  if (endpoint.includes('amazonaws.com')) return false
  return true
}

/**
 * Client S3 pour R2 ou AWS (alias STORAGE_* en prod ECS).
 */
export function getR2S3Client(): S3Client {
  const key = cacheKey()
  if (cached?.key === key) {
    return cached.client
  }

  const endpoint = getR2Endpoint()
  const accessKeyId = getR2AccessKeyId()
  const secretAccessKey = getR2SecretAccessKey()
  const region = getS3ClientRegion()

  if (!endpoint || !accessKeyId || !secretAccessKey) {
    console.warn(
      '⚠️  R2 / STORAGE credentials not configured. Media uploads will fail. ' +
        'Set R2_* or STORAGE_* (endpoint, access key id, secret).'
    )
  }

  const client = new S3Client({
    region,
    endpoint: endpoint || undefined,
    credentials:
      accessKeyId && secretAccessKey
        ? { accessKeyId, secretAccessKey }
        : undefined,
    forcePathStyle: shouldForcePathStyle(endpoint),
  })

  cached = { key, client }
  return client
}
