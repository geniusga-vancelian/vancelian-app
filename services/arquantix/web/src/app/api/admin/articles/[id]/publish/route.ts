import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { ContentStatus, TranslationStatus } from '@prisma/client'

// POST /api/admin/articles/[id]/publish
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const article = await prisma.article.findUnique({
      where: { id: params.id },
      include: {
        i18n: true,
      },
    })

    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    // Cover image is optional (public page handles empty cover)
    // Check for unapproved machine translations
    const unapprovedLocales = article.i18n
      .filter((i) => i.translationStatus === TranslationStatus.MACHINE)
      .map((i) => i.locale)

    // Publish article
    // If publishedAt is null, set it to now. Otherwise keep the existing value.
    const updated = await prisma.article.update({
      where: { id: params.id },
      data: {
        status: ContentStatus.PUBLISHED,
        publishedAt: article.publishedAt || new Date(),
      },
      include: {
        coverMedia: true,
        i18n: {
          orderBy: { locale: 'asc' },
        },
        blocks: {
          orderBy: { order: 'asc' },
        },
      },
    })

    return NextResponse.json({
      article: updated,
      warning: unapprovedLocales.length > 0
        ? `Some locales contain machine translations not approved yet: ${unapprovedLocales.join(', ')}`
        : undefined,
    })
  } catch (error) {
    console.error('Error publishing article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

