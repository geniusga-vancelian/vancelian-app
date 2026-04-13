import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

/**
 * DELETE /api/admin/sections/[sectionId]
 * Delete a section and all its content
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { sectionId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const section = await prisma.section.findUnique({
      where: { id: params.sectionId },
      include: {
        page: {
          select: { slug: true },
        },
      },
    })

    if (!section) {
      return NextResponse.json({ error: 'Section not found' }, { status: 404 })
    }

    // Delete section (cascade will delete contents)
    await prisma.section.delete({
      where: { id: params.sectionId },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting section:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









