import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { uploadFile } from '@/lib/storage/storageClient'
import { z } from 'zod'
import sharp from 'sharp'

const MAX_UPLOAD_MB = parseInt(process.env.MAX_UPLOAD_MB || '20', 10)
const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

const ALLOWED_MIME_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/gif',
  'image/webp',
  'image/svg+xml',
  'application/pdf',
  'video/mp4',
  'video/webm',
]

/**
 * POST /api/admin/media/upload
 * Upload a file to R2 and create a Media record
 */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const formData = await request.formData()
    const file = formData.get('file') as File | null
    const alt = formData.get('alt') as string | null

    if (!file) {
      return NextResponse.json({ error: 'No file provided' }, { status: 400 })
    }

    // Validate file size
    if (file.size > MAX_UPLOAD_BYTES) {
      console.error(`[Media Upload] File too large: ${file.size} bytes (max: ${MAX_UPLOAD_BYTES})`)
      return NextResponse.json(
        { error: `File size exceeds ${MAX_UPLOAD_MB}MB limit` },
        { status: 400 }
      )
    }

    // Validate MIME type
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      console.error(`[Media Upload] Invalid MIME type: ${file.type}`)
      return NextResponse.json(
        { error: `File type not allowed. Allowed types: ${ALLOWED_MIME_TYPES.join(', ')}` },
        { status: 400 }
      )
    }

    // Generate unique key
    const timestamp = Date.now()
    const random = Math.random().toString(36).substring(2, 15)
    const extension = file.name.split('.').pop() || ''
    const key = `media/${timestamp}-${random}.${extension}`

    // Read file buffer
    const arrayBuffer = await file.arrayBuffer()
    const buffer = Buffer.from(arrayBuffer)

    // Get image dimensions if it's an image
    let width: number | null = null
    let height: number | null = null

    if (file.type.startsWith('image/') && file.type !== 'image/svg+xml') {
      try {
        const metadata = await sharp(buffer).metadata()
        width = metadata.width || null
        height = metadata.height || null
      } catch (error) {
        console.warn('Failed to get image dimensions:', error)
      }
    }

    // Upload to R2
    const uploadResult = await uploadFile(buffer, key, file.type)

    // Create Media record
    const media = await prisma.media.create({
      data: {
        key: uploadResult.key,
        url: uploadResult.url,
        filename: file.name,
        mimeType: file.type,
        size: uploadResult.size,
        width,
        height,
        alt: alt || null,
        uploadedByUserId: session.userId,
      },
    })

    console.log(`[Media Upload] Success: Media ID ${media.id}, Key: ${media.key}`)
    return NextResponse.json({ media }, { status: 201 })
  } catch (error) {
    console.error('[Media Upload] Error:', error)
    const errorMessage = error instanceof Error ? error.message : 'Failed to upload media'
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    )
  }
}

