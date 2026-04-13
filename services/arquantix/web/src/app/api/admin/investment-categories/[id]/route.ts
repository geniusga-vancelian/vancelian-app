import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { z } from 'zod'

async function resolveImageUrl(mediaId: string | null, imageUrl: string | null): Promise<string | null> {
  if (mediaId) {
    try {
      const media = await prisma.media.findUnique({ where: { id: mediaId } })
      if (media) {
        try {
          return await getPresignedUrl(media.key, 3600)
        } catch {
          return media.url
        }
      }
    } catch {
      // fallback to imageUrl
    }
  }
  return imageUrl
}

/** GET /api/admin/investment-categories/[id] */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params
    const category = await prisma.investmentCategory.findUnique({
      where: { id },
      include: { media: true },
    })

    if (!category) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    const imageResolved = await resolveImageUrl(category.mediaId, category.imageUrl)
    return NextResponse.json({
      category: {
        ...category,
        imageResolved,
      },
    })
  } catch (error) {
    console.error('Error fetching investment category:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

const updateSchema = z.object({
  label: z.string().min(1).max(200).optional(),
  description: z.string().max(2000).optional().nullable(),
  mediaId: z.string().optional().nullable(),
  sortOrder: z.number().int().optional(),
})

/** PATCH /api/admin/investment-categories/[id] */
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params
    const existing = await prisma.investmentCategory.findUnique({ where: { id } })
    if (!existing) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    const body = await request.json()
    const data = updateSchema.parse(body)

    const updatePayload: {
      label?: string
      description?: string | null
      mediaId?: string | null
      sortOrder?: number
    } = {}
    if (data.label !== undefined) updatePayload.label = data.label.trim()
    if (data.description !== undefined) updatePayload.description = data.description?.trim() || null
    if (data.mediaId !== undefined) updatePayload.mediaId = data.mediaId || null
    if (data.sortOrder !== undefined) updatePayload.sortOrder = data.sortOrder

    const category = await prisma.investmentCategory.update({
      where: { id },
      data: updatePayload,
    })

    return NextResponse.json({ category })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: error.message, details: error.flatten() }, { status: 400 })
    }
    console.error('Error updating investment category:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/** DELETE /api/admin/investment-categories/[id] — Suppression uniquement si aucun projet n’est attaché. */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params
    const category = await prisma.investmentCategory.findUnique({ where: { id } })
    if (!category) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    const projectsCount = await prisma.project.count({
      where: {
        investmentCategory: {
          equals: category.label,
          mode: 'insensitive',
        },
      },
    })

    if (projectsCount > 0) {
      return NextResponse.json(
        {
          error: 'Impossible de supprimer cette catégorie : des projets ou offres exclusives y sont encore rattachés.',
          projectsCount,
        },
        { status: 409 }
      )
    }

    await prisma.investmentCategory.delete({ where: { id } })
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting investment category:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
