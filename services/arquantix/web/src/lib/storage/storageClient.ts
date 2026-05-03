/**
 * Storage Client for Cloudflare R2
 * 
 * Provides upload, delete, and URL generation functions
 */

import { PutObjectCommand, DeleteObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'
import { r2Client } from './r2-client'
import { assertR2Configured } from './r2Env'

const bucketName = process.env.R2_BUCKET_NAME || 'arquantix-media'
const publicUrl = process.env.R2_PUBLIC_URL // Optional custom domain for public URLs
const endpoint = process.env.R2_ENDPOINT

export interface UploadResult {
  key: string
  url: string
  size: number
  contentType: string
}

/**
 * Upload a file to R2
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

  // Generate public URL
  const url = getPublicUrl(key)

  return {
    key,
    url,
    size: file.length,
    contentType,
  }
}

/**
 * Delete a file from R2
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
 * Get public URL for a file
 * 
 * If R2_PUBLIC_URL is set, uses that.
 * Otherwise, uses the R2 endpoint URL format.
 */
export function getPublicUrl(key: string): string {
  if (publicUrl) {
    // Remove trailing slash if present
    const baseUrl = publicUrl.replace(/\/$/, '')
    return `${baseUrl}/${key}`
  }

  // Fallback to R2 endpoint URL format
  // Extract account ID from endpoint if available
  if (endpoint) {
    const match = endpoint.match(/https:\/\/([^.]+)\.r2\.cloudflarestorage\.com/)
    if (match && match[1]) {
      return `https://pub-${match[1]}.r2.dev/${key}`
    }
  }

  throw new Error('R2_ENDPOINT not configured or invalid format')
}

/**
 * Generate a presigned URL for private access (if needed)
 */
export async function getPresignedUrl(key: string, expiresIn: number = 3600): Promise<string> {
  assertR2Configured()

  const command = new GetObjectCommand({
    Bucket: bucketName,
    Key: key,
  })

  return getSignedUrl(r2Client, command, { expiresIn })
}

