import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// DELETE /api/admin/projects/[id]/gallery/[projectMediaId]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string; projectMediaId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Verify project exists
    const project = await prisma.project.findUnique({
      where: { id: params.id },
    })

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Verify project media exists and belongs to this project
    const projectMedia = await prisma.projectMedia.findUnique({
      where: { id: params.projectMediaId },
    })

    if (!projectMedia) {
      return NextResponse.json({ error: 'Project media not found' }, { status: 404 })
    }

    if (projectMedia.projectId !== params.id) {
      return NextResponse.json(
        { error: 'Project media does not belong to this project' },
        { status: 403 }
      )
    }

    // Delete project media
    await prisma.projectMedia.delete({
      where: { id: params.projectMediaId },
    })

    return NextResponse.json({ message: 'Media removed from gallery' })
  } catch (error) {
    console.error('Error deleting project media:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









