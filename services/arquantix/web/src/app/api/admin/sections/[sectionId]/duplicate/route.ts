import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { ContentStatus } from '@prisma/client'
import { defaultLocale } from '@/config/locales'

/**
 * POST /api/admin/sections/[sectionId]/duplicate
 * Duplicate a section (clone data and add after original)
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { sectionId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const originalSection = await prisma.section.findUnique({
      where: { id: params.sectionId },
      include: {
        page: {
          include: {
            sections: {
              orderBy: { order: 'desc' },
              take: 1,
            },
          },
        },
        contents: {
          where: {
            locale: defaultLocale,
          },
        },
      },
    })

    if (!originalSection) {
      return NextResponse.json({ error: 'Section not found' }, { status: 404 })
    }

    // Get the last order from the page
    const nextOrder = originalSection.page.sections.length > 0
      ? originalSection.page.sections[0].order + 1
      : originalSection.order + 1

    // Generate new key (append -copy or -copy-2, etc.)
    let newKey = `${originalSection.key}-copy`
    let counter = 1
    while (
      await prisma.section.findUnique({
        where: {
          pageId_key: {
            pageId: originalSection.pageId,
            key: newKey,
          },
        },
      })
    ) {
      counter++
      newKey = `${originalSection.key}-copy-${counter}`
    }

    // Get published content data (fallback to draft if no published)
    const publishedContent = originalSection.contents.find((c) => c.status === ContentStatus.PUBLISHED)
    const draftContent = originalSection.contents.find((c) => c.status === ContentStatus.DRAFT)
    const dataToClone = publishedContent?.data || draftContent?.data || {}

    // Create duplicated section
    const duplicatedSection = await prisma.section.create({
      data: {
        pageId: originalSection.pageId,
        key: newKey,
        order: nextOrder,
        schemaVersion: originalSection.schemaVersion,
        contents: {
          create: [
            {
              locale: defaultLocale,
              status: ContentStatus.DRAFT,
              data: dataToClone,
              updatedByUserId: session.userId,
            },
            {
              locale: defaultLocale,
              status: ContentStatus.PUBLISHED,
              data: dataToClone,
              updatedByUserId: session.userId,
            },
          ],
        },
      },
      include: {
        contents: {
          select: {
            id: true,
            locale: true,
            status: true,
          },
        },
      },
    })

    return NextResponse.json({ section: duplicatedSection }, { status: 201 })
  } catch (error) {
    console.error('Error duplicating section:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









