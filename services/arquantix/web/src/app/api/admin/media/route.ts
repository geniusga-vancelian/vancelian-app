import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import type { Prisma } from '@prisma/client'

type MediaTypeFilter = 'image' | 'video' | 'document'

function mediaTypeWhere(type: MediaTypeFilter | null): Prisma.MediaWhereInput {
  if (type === 'image') return { mimeType: { startsWith: 'image/' } }
  if (type === 'video') return { mimeType: { startsWith: 'video/' } }
  if (type === 'document') {
    return {
      NOT: [
        { mimeType: { startsWith: 'image/' } },
        { mimeType: { startsWith: 'video/' } },
      ],
    }
  }
  return {}
}

function parseMediaType(raw: string | null): MediaTypeFilter | null {
  if (raw === 'image' || raw === 'video' || raw === 'document') return raw
  return null
}

/**
 * GET /api/admin/media
 * List all media with optional search, type filter, and pagination
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const search = searchParams.get('search') || ''
    const limit = Math.min(Math.max(parseInt(searchParams.get('limit') || '50', 10) || 50, 1), 200)
    const offset = Math.max(parseInt(searchParams.get('offset') || '0', 10) || 0, 0)
    const type = parseMediaType(searchParams.get('type'))
    const includeFacets = searchParams.get('facets') !== '0'

    const searchWhere: Prisma.MediaWhereInput = search
      ? {
          OR: [
            { filename: { contains: search, mode: 'insensitive' as const } },
            { alt: { contains: search, mode: 'insensitive' as const } },
          ],
        }
      : {}

    const where: Prisma.MediaWhereInput = {
      AND: [searchWhere, mediaTypeWhere(type)],
    }

    const facetBaseWhere: Prisma.MediaWhereInput = searchWhere

    const queries: [
      ReturnType<typeof prisma.media.findMany>,
      ReturnType<typeof prisma.media.count>,
      ReturnType<typeof prisma.media.count> | Promise<number>,
      ReturnType<typeof prisma.media.count> | Promise<number>,
      ReturnType<typeof prisma.media.count> | Promise<number>,
    ] = [
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
      includeFacets ? prisma.media.count({ where: facetBaseWhere }) : Promise.resolve(0),
      includeFacets
        ? prisma.media.count({ where: { AND: [facetBaseWhere, mediaTypeWhere('image')] } })
        : Promise.resolve(0),
      includeFacets
        ? prisma.media.count({ where: { AND: [facetBaseWhere, mediaTypeWhere('video')] } })
        : Promise.resolve(0),
    ]

    const [mediaItems, total, allCount, imagesCount, videosCount] = await Promise.all(queries)
    const documentsCount = includeFacets
      ? await prisma.media.count({
          where: { AND: [facetBaseWhere, mediaTypeWhere('document')] },
        })
      : 0

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
      ...(includeFacets
        ? {
            facets: {
              all: allCount,
              images: imagesCount,
              videos: videosCount,
              documents: documentsCount,
            },
          }
        : {}),
    })
  } catch (error) {
    console.error('Error fetching media:', error)
    return NextResponse.json(
      { error: 'Failed to fetch media' },
      { status: 500 }
    )
  }
}

