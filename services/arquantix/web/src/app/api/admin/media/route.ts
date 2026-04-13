import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { z } from 'zod'

/**
 * GET /api/admin/media
 * List all media with optional search
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const search = searchParams.get('search') || ''
    const limit = parseInt(searchParams.get('limit') || '50', 10)
    const offset = parseInt(searchParams.get('offset') || '0', 10)

    const where = search
      ? {
          OR: [
            { filename: { contains: search, mode: 'insensitive' as const } },
            { alt: { contains: search, mode: 'insensitive' as const } },
          ],
        }
      : {}

    const [mediaItems, total] = await Promise.all([
      prisma.media.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        take: limit,
        skip: offset,
        include: {
          uploadedBy: {
            select: {
              id: true,
              email: true,
            },
          },
        },
      }),
      prisma.media.count({ where }),
    ])

    // Generate presigned URLs for images (valid for 1 hour)
    // This ensures images are accessible even if bucket is not public
    const mediaWithPresignedUrls = await Promise.all(
      mediaItems.map(async (item) => {
        try {
          const presignedUrl = await getPresignedUrl(item.key, 3600)
          return {
            ...item,
            url: presignedUrl, // Use presigned URL for display
            publicUrl: item.url, // Keep original URL as fallback
          }
        } catch (error) {
          console.error(`[Media API] Failed to generate presigned URL for ${item.key}:`, error)
          // Fallback to original URL if presigned URL generation fails
          return {
            ...item,
            publicUrl: item.url,
          }
        }
      })
    )

    return NextResponse.json({
      media: mediaWithPresignedUrls,
      pagination: {
        total,
        limit,
        offset,
        hasMore: offset + limit < total,
      },
    })
  } catch (error) {
    console.error('Error fetching media:', error)
    return NextResponse.json(
      { error: 'Failed to fetch media' },
      { status: 500 }
    )
  }
}

