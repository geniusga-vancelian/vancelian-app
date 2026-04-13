import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const colorHexSchema = z.string().regex(/^#(?:[0-9a-fA-F]{6})$/, 'Invalid hex color')

const updateCollectionSchema = z.object({
  slug: z.string().min(1).optional(),
  iconKey: z.string().min(1).optional(),
  colorHex: colorHexSchema.optional(),
  order: z.number().int().optional(),
  isPublished: z.boolean().optional(),
})

// GET /api/admin/help/collections/[id]
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const collection = await prisma.helpCollection.findUnique({
      where: { id: params.id },
      include: {
        i18n: true,
        categories: {
          orderBy: { order: 'asc' },
        },
      },
    })

    if (!collection) {
      return NextResponse.json({ error: 'Collection not found' }, { status: 404 })
    }

    return NextResponse.json({ collection })
  } catch (error) {
    console.error('Error fetching collection:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// PUT /api/admin/help/collections/[id]
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = updateCollectionSchema.parse(body)

    const collection = await prisma.helpCollection.update({
      where: { id: params.id },
      data: validated,
    })

    return NextResponse.json({ collection })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating collection:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// DELETE /api/admin/help/collections/[id]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Check if collection has categories
    const collection = await prisma.helpCollection.findUnique({
      where: { id: params.id },
      include: {
        _count: {
          select: {
            categories: true,
          },
        },
      },
    })

    if (!collection) {
      return NextResponse.json({ error: 'Collection not found' }, { status: 404 })
    }

    if (collection._count.categories > 0) {
      return NextResponse.json(
        { error: 'Cannot delete collection with categories' },
        { status: 400 }
      )
    }

    await prisma.helpCollection.delete({
      where: { id: params.id },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting collection:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}


