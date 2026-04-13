import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const addMediaSchema = z.object({
  mediaId: z.string().min(1, 'Media ID is required'),
})

const reorderSchema = z.object({
  orderedProjectMediaIds: z.array(z.string()),
})

// POST /api/admin/projects/[id]/gallery
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { mediaId } = addMediaSchema.parse(body)

    // Verify project exists
    const project = await prisma.project.findUnique({
      where: { id: params.id },
      include: {
        projectMedia: {
          orderBy: { order: 'desc' },
          take: 1,
        },
      },
    })

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Check if media exists
    const media = await prisma.media.findUnique({
      where: { id: mediaId },
    })

    if (!media) {
      return NextResponse.json({ error: 'Media not found' }, { status: 404 })
    }

    // Get next order (last order + 1)
    const nextOrder =
      project.projectMedia.length > 0 ? project.projectMedia[0].order + 1 : 0

    // Create project media
    const projectMedia = await prisma.projectMedia.create({
      data: {
        projectId: params.id,
        mediaId,
        order: nextOrder,
      },
      include: {
        media: true,
      },
    })

    return NextResponse.json({ projectMedia }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error adding media to gallery:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/projects/[id]/gallery/reorder
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
    const { orderedProjectMediaIds } = reorderSchema.parse(body)

    // Verify project exists
    const project = await prisma.project.findUnique({
      where: { id: params.id },
    })

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Update orders
    const updates = orderedProjectMediaIds.map((projectMediaId, index) =>
      prisma.projectMedia.update({
        where: { id: projectMediaId },
        data: { order: index },
      })
    )

    await prisma.$transaction(updates)

    return NextResponse.json({ message: 'Gallery reordered successfully' })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error reordering gallery:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









