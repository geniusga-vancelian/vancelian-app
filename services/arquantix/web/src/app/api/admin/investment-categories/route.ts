import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { z } from 'zod'

function slugFromLabel(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}

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

/** GET /api/admin/investment-categories — Liste des catégories (admin). */
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const categories = await prisma.investmentCategory.findMany({
      orderBy: { sortOrder: 'asc' },
      include: { media: true },
    })

    const withResolvedImage = await Promise.all(
      categories.map(async (c) => ({
        id: c.id,
        slug: c.slug,
        label: c.label,
        description: c.description ?? null,
        imageUrl: c.imageUrl ?? null,
        mediaId: c.mediaId ?? null,
        sortOrder: c.sortOrder,
        imageResolved: await resolveImageUrl(c.mediaId, c.imageUrl),
      }))
    )

    return NextResponse.json({ categories: withResolvedImage })
  } catch (error) {
    console.error('Error fetching investment categories:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

const createSchema = z.object({
  label: z.string().min(1).max(200),
  description: z.string().max(2000).optional().nullable(),
  mediaId: z.string().optional().nullable(),
  sortOrder: z.number().int().optional(),
})

/** POST /api/admin/investment-categories — Créer une catégorie. */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { label, description, mediaId, sortOrder } = createSchema.parse(body)

    const slug = slugFromLabel(label)
    const existing = await prisma.investmentCategory.findUnique({ where: { slug } })
    if (existing) {
      return NextResponse.json(
        { error: 'Une catégorie avec ce libellé (slug) existe déjà.' },
        { status: 409 }
      )
    }

    const maxOrder = await prisma.investmentCategory.aggregate({
      _max: { sortOrder: true },
    })
    const order = sortOrder ?? (maxOrder._max.sortOrder ?? -1) + 1

    const category = await prisma.investmentCategory.create({
      data: {
        slug,
        label: label.trim(),
        description: description?.trim() || null,
        mediaId: mediaId || null,
        sortOrder: order,
      },
    })

    return NextResponse.json({ category })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: error.message, details: error.flatten() }, { status: 400 })
    }
    console.error('Error creating investment category:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
