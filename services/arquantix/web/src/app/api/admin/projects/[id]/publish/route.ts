import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { ContentStatus, TranslationStatus } from '@prisma/client'

// POST /api/admin/projects/[id]/publish
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const project = await prisma.project.findUnique({
      where: { id: params.id },
      include: {
        i18n: true,
      },
    })

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Check for unapproved machine translations
    const unapprovedLocales = project.i18n
      .filter((i) => i.translationStatus === TranslationStatus.MACHINE)
      .map((i) => i.locale)

    // Publish project
    const updated = await prisma.project.update({
      where: { id: params.id },
      data: {
        status: ContentStatus.PUBLISHED,
      },
      include: {
        coverMedia: true,
        i18n: {
          orderBy: { locale: 'asc' },
        },
      },
    })

    return NextResponse.json({
      project: updated,
      warning: unapprovedLocales.length > 0
        ? `Some locales contain machine translations not approved yet: ${unapprovedLocales.join(', ')}`
        : undefined,
    })
  } catch (error) {
    console.error('Error publishing project:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

