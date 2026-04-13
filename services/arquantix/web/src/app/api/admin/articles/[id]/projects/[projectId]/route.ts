import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// DELETE /api/admin/articles/[id]/projects/[projectId]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string; projectId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const articleProject = await prisma.articleProject.findUnique({
      where: {
        articleId_projectId: {
          articleId: params.id,
          projectId: params.projectId,
        },
      },
    })

    if (!articleProject) {
      return NextResponse.json(
        { error: 'Project link not found' },
        { status: 404 }
      )
    }

    await prisma.articleProject.delete({
      where: {
        articleId_projectId: {
          articleId: params.id,
          projectId: params.projectId,
        },
      },
    })

    return NextResponse.json({ message: 'Project unlinked from article' })
  } catch (error) {
    console.error('Error unlinking project from article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









