import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { ContentStatus } from '@prisma/client'
import { awaitRouteParams } from '@/lib/api/routeParams'

// POST /api/admin/articles/[id]/unpublish
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } | Promise<{ id: string }> }
) {
  try {
    const { id } = await awaitRouteParams(params)
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const article = await prisma.article.findUnique({
      where: { id },
    })

    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    // Unpublish article (keep publishedAt, don't reset it)
    const updated = await prisma.article.update({
      where: { id },
      data: {
        status: ContentStatus.DRAFT,
        // publishedAt is NOT reset - we keep it
      },
    })

    return NextResponse.json({ article: updated })
  } catch (error) {
    console.error('Error unpublishing article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

