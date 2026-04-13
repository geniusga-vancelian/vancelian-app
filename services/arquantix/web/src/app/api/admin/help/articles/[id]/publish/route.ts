import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// POST /api/admin/help/articles/[id]/publish
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const article = await prisma.helpArticle.findUnique({
      where: { id: params.id },
      include: {
        i18n: {
          where: { locale: 'fr' },
          take: 1,
        },
      },
    })

    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    const i18n = article.i18n[0]
    if (!i18n) {
      return NextResponse.json(
        { error: 'Article must have French content before publishing' },
        { status: 400 }
      )
    }

    const updateData: any = {
      status: 'PUBLISHED',
    }

    // Set publishedAt if not already set
    if (!article.publishedAt) {
      updateData.publishedAt = new Date()
    }

    const updated = await prisma.helpArticle.update({
      where: { id: params.id },
      data: updateData,
    })

    return NextResponse.json({ article: updated })
  } catch (error) {
    console.error('Error publishing article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}


