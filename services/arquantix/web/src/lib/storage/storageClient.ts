/**
 * Storage Client for Cloudflare R2
 * 
 * Provides upload, delete, and URL generation functions
 */

import { PutObjectCommand, DeleteObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'
import { getR2S3Client } from './r2-client'
import {
  assertR2Configured,
  getR2BucketName,
  getR2Endpoint,
  getR2PublicUrl,
  getS3ClientRegion,
  isR2CloudflareEndpoint,
} from './r2Env'

const bucketName = getR2BucketName()
const publicUrl = getR2PublicUrl()
const endpoint = getR2Endpoint()

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

  await getR2S3Client().send(command)

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

  await getR2S3Client().send(command)
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

  if (endpoint) {
    if (isR2CloudflareEndpoint()) {
      const match = endpoint.match(/https:\/\/([^.]+)\.r2\.cloudflarestorage\.com/)
      if (match && match[1]) {
        return `https://pub-${match[1]}.r2.dev/${key}`
      }
    }
    if (endpoint.includes('amazonaws.com')) {
      const region = getS3ClientRegion()
      return `https://${bucketName}.s3.${region}.amazonaws.com/${key}`
    }
  }

  throw new Error('Storage endpoint not configured or unsupported (R2 / S3)')
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

  return getSignedUrl(getR2S3Client(), command, { expiresIn })
}

