/**
 * Script to sync media files from R2 to database
 * This script lists all files in R2 and creates/updates Media records in the database
 */

import { PrismaClient } from '@prisma/client'
import { S3Client, ListObjectsV2Command, HeadObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'
import { GetObjectCommand } from '@aws-sdk/client-s3'

const prisma = new PrismaClient()

// R2 configuration from environment variables
const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID || process.env.CLOUDFLARE_ACCOUNT_ID
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID
const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY
const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME || 'arquantix-media'
const R2_ENDPOINT = process.env.R2_ENDPOINT || (R2_ACCOUNT_ID ? `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com` : '')

if (!R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY || !R2_BUCKET_NAME || !R2_ENDPOINT) {
  console.error('❌ Missing R2 configuration. Please check your .env file.')
  console.error('Required: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_ENDPOINT (or R2_ACCOUNT_ID)')
  process.exit(1)
}

const s3Client = new S3Client({
  region: 'auto',
  endpoint: R2_ENDPOINT,
  credentials: {
    accessKeyId: R2_ACCESS_KEY_ID,
    secretAccessKey: R2_SECRET_ACCESS_KEY,
  },
})

async function getFileMetadata(key: string) {
  try {
    const command = new HeadObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: key,
    })
    const response = await s3Client.send(command)
    
    return {
      size: response.ContentLength || 0,
      mimeType: response.ContentType || 'application/octet-stream',
      lastModified: response.LastModified,
      metadata: response.Metadata || {},
    }
  } catch (error) {
    console.error(`Error getting metadata for ${key}:`, error)
    return null
  }
}

async function getPublicUrl(key: string): Promise<string> {
  // Try to get a presigned URL (valid for 1 hour)
  try {
    const command = new GetObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: key,
    })
    const url = await getSignedUrl(s3Client, command, { expiresIn: 3600 })
    return url
  } catch (error) {
    console.error(`Error generating URL for ${key}:`, error)
    // Fallback: construct a basic URL (may not work if R2 is private)
    return `${R2_ENDPOINT}/${R2_BUCKET_NAME}/${key}`
  }
}

async function syncMediaFromR2() {
  console.log('🔄 Starting R2 media sync...')
  console.log(`📦 Bucket: ${R2_BUCKET_NAME}`)
  console.log(`🌐 Endpoint: ${R2_ENDPOINT}`)
  console.log('')

  try {
    let continuationToken: string | undefined
    let totalFiles = 0
    let synced = 0
    let skipped = 0
    let errors = 0

    do {
      const command = new ListObjectsV2Command({
        Bucket: R2_BUCKET_NAME,
        ContinuationToken: continuationToken,
      })

      const response = await s3Client.send(command)
      const objects = response.Contents || []

      console.log(`📋 Found ${objects.length} objects in this batch...`)

      for (const object of objects) {
        if (!object.Key) continue
        
        totalFiles++
        const key = object.Key

        try {
          // Skip if it's a directory (ends with /)
          if (key.endsWith('/')) {
            skipped++
            continue
          }

          // Get file metadata
          const metadata = await getFileMetadata(key)
          if (!metadata) {
            errors++
            continue
          }

          // Extract filename from key (get the last part after /)
          const filename = key.split('/').pop() || key

          // Generate public URL
          const url = await getPublicUrl(key)

          // Create or update Media record
          const media = await prisma.media.upsert({
            where: { key },
            update: {
              url,
              filename,
              mimeType: metadata.mimeType,
              size: metadata.size,
            },
            create: {
              key,
              url,
              filename,
              mimeType: metadata.mimeType,
              size: metadata.size,
              // Note: We can't determine width/height/alt without processing the image
              // These can be updated later through the admin UI
            },
          })

          synced++
          console.log(`  ✅ Synced: ${filename} (${(metadata.size / 1024).toFixed(2)} KB)`)

        } catch (error) {
          errors++
          console.error(`  ❌ Error syncing ${key}:`, error)
        }
      }

      continuationToken = response.NextContinuationToken
    } while (continuationToken)

    console.log('')
    console.log('📊 Sync Summary:')
    console.log(`  Total files found: ${totalFiles}`)
    console.log(`  Synced: ${synced}`)
    console.log(`  Skipped (directories): ${skipped}`)
    console.log(`  Errors: ${errors}`)
    console.log('')
    console.log('✅ Sync completed!')

  } catch (error) {
    console.error('❌ Fatal error during sync:', error)
    process.exit(1)
  } finally {
    await prisma.$disconnect()
  }
}

syncMediaFromR2()


