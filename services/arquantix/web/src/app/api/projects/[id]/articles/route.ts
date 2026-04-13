import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { defaultLocale, getLocaleOrDefault } from '@/config/locales'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { getArticlesByProject } from '@/lib/blog/articleService'

/**
 * GET /api/projects/[id]/articles
 * Articles linked to this project via the related project section (article_projects).
 * Used by the mobile app for the "A la une" module on the project detail page.
 * Query: locale (optional), limit (optional, default 20).
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params
    const { searchParams } = new URL(request.url)
    const locale = getLocaleOrDefault(searchParams.get('locale') || defaultLocale)
    const limit = Math.min(
      Math.max(parseInt(searchParams.get('limit') || '20', 10), 1),
      50
    )

    const project = await prisma.project.findUnique({
      where: { id: projectId, status: ContentStatus.PUBLISHED },
      select: { id: true },
    })
    if (!project) {
      return NextResponse.json({ articles: [] }, { status: 200 })
    }

    const articles = await getArticlesByProject(
      { projectId, locale, limit },
      calculateReadingTime
    )

    return NextResponse.json({ articles })
  } catch (error) {
    console.error('Error fetching project articles:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
