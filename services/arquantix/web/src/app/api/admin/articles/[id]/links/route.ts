import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { ArticleLinkKind } from '@prisma/client'
import { ASSET_LABELS } from '@/lib/admin/asset-labels'

// GET /api/admin/articles/[id]/links
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const links = await prisma.articleLink.findMany({
      where: { articleId: params.id },
      orderBy: { createdAt: 'asc' },
    })

    const vaultSlugs = links.filter((l) => l.kind === 'VAULT').map((l) => l.targetId)
    const vaultTitles =
      vaultSlugs.length > 0
        ? await prisma.page.findMany({
            where: { slug: { in: vaultSlugs } },
            select: { slug: true, title: true },
          })
        : []
    const vaultTitleBySlug = Object.fromEntries(
      vaultTitles.map((p) => [p.slug, p.title || p.slug])
    )

    const linksWithLabel = links.map((l) => ({
      ...l,
      label:
        l.kind === 'ASSET'
          ? ASSET_LABELS[l.targetId] || `${l.targetId.toUpperCase()}`
          : vaultTitleBySlug[l.targetId] || l.targetId,
    }))

    return NextResponse.json({ links: linksWithLabel })
  } catch (error) {
    console.error('Error fetching article links:', error)
    const message =
      process.env.NODE_ENV === 'development' && error instanceof Error
        ? error.message
        : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

// POST /api/admin/articles/[id]/links
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
    const { kind, targetId } = body

    if (!kind || !targetId || typeof targetId !== 'string') {
      return NextResponse.json(
        { error: 'kind and targetId are required' },
        { status: 400 }
      )
    }

    const validKind = kind === 'ASSET' || kind === 'VAULT'
    if (!validKind) {
      return NextResponse.json(
        { error: 'kind must be ASSET or VAULT' },
        { status: 400 }
      )
    }

    const normalizedTargetId = targetId.trim().toLowerCase()

    const article = await prisma.article.findUnique({
      where: { id: params.id },
    })
    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    const link = await prisma.articleLink.upsert({
      where: {
        articleId_kind_targetId: {
          articleId: params.id,
          kind: kind as ArticleLinkKind,
          targetId: normalizedTargetId,
        },
      },
      create: {
        articleId: params.id,
        kind: kind as ArticleLinkKind,
        targetId: normalizedTargetId,
      },
      update: {},
    })

    return NextResponse.json({ link })
  } catch (error) {
    if (
      error instanceof Error &&
      (error.message.includes('Unique constraint') ||
        error.message.includes('article_links_article_id_kind_target_id_key'))
    ) {
      return NextResponse.json(
        { error: 'This item is already linked to the article' },
        { status: 400 }
      )
    }
    console.error('Error linking to article:', error)
    const message =
      process.env.NODE_ENV === 'development' && error instanceof Error
        ? error.message
        : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
