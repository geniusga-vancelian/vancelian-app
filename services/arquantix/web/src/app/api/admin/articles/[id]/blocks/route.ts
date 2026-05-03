import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { ArticleBlockType, Prisma } from '@prisma/client'
import {
  articleBlockEnumHintPayload,
  isArticleBlockEnumDatabaseError,
} from '@/lib/api/articleBlockEnumDbError'
import { safeParseArticleBlockData } from '@/lib/blog/articleBlockDataSchemas'
import { awaitRouteParams } from '@/lib/api/routeParams'
import { adminRouteErrorBody } from '@/lib/api/adminRouteErrorBody'

const createBlockSchema = z.object({
  type: z.nativeEnum(ArticleBlockType),
  data: z.any().optional().default({}),
  order: z.number().int().optional(),
})

// GET /api/admin/articles/[id]/blocks
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } | Promise<{ id: string }> }
) {
  try {
    const { id: articleId } = await awaitRouteParams(params)
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const blocks = await prisma.articleBlock.findMany({
      where: { articleId },
      orderBy: { order: 'asc' },
    })

    return NextResponse.json({ blocks })
  } catch (error) {
    console.error('Error fetching blocks:', error)
    return NextResponse.json(adminRouteErrorBody(error), { status: 500 })
  }
}

// POST /api/admin/articles/[id]/blocks
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } | Promise<{ id: string }> }
) {
  try {
    const { id: articleId } = await awaitRouteParams(params)
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const article = await prisma.article.findUnique({
      where: { id: articleId },
      select: { id: true },
    })
    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    let body: unknown
    try {
      body = await request.json()
    } catch {
      return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
    }
    const validated = createBlockSchema.parse(body)

    if (validated.type === ArticleBlockType.IMAGE) {
      return NextResponse.json(
        {
          error: 'Le bloc Image n\'est plus disponible. Utilisez le type Carrousel (même pour une seule image).',
        },
        { status: 400 }
      )
    }

    // Get max order
    const maxOrder = await prisma.articleBlock.findFirst({
      where: { articleId },
      orderBy: { order: 'desc' },
      select: { order: true },
    })

    const order = validated.order !== undefined ? validated.order : (maxOrder?.order ?? -1) + 1

    const raw = validated.data
    const parsedData = safeParseArticleBlockData(validated.type, raw === undefined || raw === null ? {} : raw)
    if (!parsedData.success) {
      return NextResponse.json(
        { error: 'Invalid block data', issues: parsedData.issues },
        { status: 400 },
      )
    }
    const dataJson: Prisma.InputJsonValue = JSON.parse(JSON.stringify(parsedData.data)) as Prisma.InputJsonValue

    const block = await prisma.articleBlock.create({
      data: {
        articleId,
        type: validated.type,
        data: dataJson,
        order,
      },
    })

    return NextResponse.json({ block }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    if (isArticleBlockEnumDatabaseError(error)) {
      console.error('Error creating block (ArticleBlockType enum / DB):', error)
      return NextResponse.json(
        { ...articleBlockEnumHintPayload(), ...adminRouteErrorBody(error) },
        { status: 500 },
      )
    }
    console.error('Error creating block:', error)
    return NextResponse.json(adminRouteErrorBody(error), { status: 500 })
  }
}









