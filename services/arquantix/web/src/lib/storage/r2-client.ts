/**
 * Storage S3 Client — agnostique AWS S3 / Cloudflare R2.
 *
 * En prod (AWS) on lit `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY_ID`,
 * `STORAGE_SECRET_ACCESS_KEY`, `STORAGE_REGION` (par défaut `us-east-1`).
 * En dev local R2 on accepte les anciens `R2_*` (région forcée à `auto` pour R2).
 *
 * L'export historique `r2Client` est conservé pour ne pas casser les imports existants.
 */

import { S3Client } from '@aws-sdk/client-s3'
import { isR2Backend } from './r2Env'

const endpoint =
  process.env.STORAGE_ENDPOINT?.trim() || process.env.R2_ENDPOINT?.trim() || ''
const accessKeyId =
  process.env.STORAGE_ACCESS_KEY_ID?.trim() || process.env.R2_ACCESS_KEY_ID?.trim() || ''
const secretAccessKey =
  process.env.STORAGE_SECRET_ACCESS_KEY?.trim() ||
  process.env.R2_SECRET_ACCESS_KEY?.trim() ||
  ''

const region = isR2Backend()
  ? 'auto'
  : process.env.STORAGE_REGION?.trim() || process.env.AWS_REGION?.trim() || 'us-east-1'

if (!endpoint || !accessKeyId || !secretAccessKey) {
  console.warn(
    '⚠️  Storage credentials not configured. Media uploads will fail. ' +
      'Set STORAGE_ENDPOINT, STORAGE_ACCESS_KEY_ID, STORAGE_SECRET_ACCESS_KEY ' +
      '(or legacy R2_* equivalents) in your environment.'
  )
}

/**
 * S3Client utilisable indifféremment pour AWS S3 ou Cloudflare R2.
 *
 * Pour AWS S3 natif : `endpoint` peut être omis (le SDK déduit l'endpoint régional).
 * On le passe quand il est défini explicitement (utile pour R2 ou un endpoint custom).
 */
export const r2Client = new S3Client({
  region,
  endpoint: endpoint || undefined,
  forcePathStyle: isR2Backend(),
  credentials:
    accessKeyId && secretAccessKey
      ? {
          accessKeyId,
          secretAccessKey,
        }
      : undefined,
})

export const storageClient = r2Client
