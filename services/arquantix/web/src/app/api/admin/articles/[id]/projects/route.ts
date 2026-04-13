import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// GET /api/admin/articles/[id]/projects
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const articleProjects = await prisma.articleProject.findMany({
      where: { articleId: params.id },
      include: {
        project: {
          include: {
            i18n: {
              orderBy: { locale: 'asc' },
            },
            coverMedia: true,
          },
        },
      },
      orderBy: { createdAt: 'asc' },
    })

    return NextResponse.json({ projects: articleProjects })
  } catch (error) {
    console.error('Error fetching article projects:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/articles/[id]/projects
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
    const { projectId } = body

    if (!projectId || typeof projectId !== 'string') {
      return NextResponse.json(
        { error: 'projectId is required' },
        { status: 400 }
      )
    }

    // Verify article exists
    const article = await prisma.article.findUnique({
      where: { id: params.id },
    })

    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    // Verify project exists
    const project = await prisma.project.findUnique({
      where: { id: projectId },
    })

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Create link (or return existing)
    const articleProject = await prisma.articleProject.upsert({
      where: {
        articleId_projectId: {
          articleId: params.id,
          projectId: projectId,
        },
      },
      create: {
        articleId: params.id,
        projectId: projectId,
      },
      update: {},
      include: {
        project: {
          include: {
            i18n: {
              orderBy: { locale: 'asc' },
            },
            coverMedia: true,
          },
        },
      },
    })

    return NextResponse.json({ project: articleProject })
  } catch (error) {
    if (error instanceof Error && error.message.includes('Unique constraint')) {
      return NextResponse.json(
        { error: 'Project already linked to this article' },
        { status: 400 }
      )
    }
    console.error('Error linking project to article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









