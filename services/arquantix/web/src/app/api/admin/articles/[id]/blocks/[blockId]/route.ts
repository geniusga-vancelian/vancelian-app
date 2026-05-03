import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { ArticleBlockType, Prisma, TranslationStatus } from '@prisma/client'
import { awaitRouteParams } from '@/lib/api/routeParams'
import { adminRouteErrorBody } from '@/lib/api/adminRouteErrorBody'
import { defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import { safeParseArticleBlockData } from '@/lib/blog/articleBlockDataSchemas'

const updateBlockSchema = z.object({
  type: z.nativeEnum(ArticleBlockType).optional(),
  data: z.any().optional(),
  order: z.number().int().optional(),
  /** Locale d’édition (même sémantique que le GET : merge `article_block_i18n` + `article_blocks.data`). */
  locale: z.string().optional(),
})

// PUT /api/admin/articles/[id]/blocks/[blockId]
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string; blockId: string } | Promise<{ id: string; blockId: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id: articleId, blockId } = await awaitRouteParams(params)

    let body: unknown
    try {
      body = await request.json()
    } catch {
      return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
    }
    const validated = updateBlockSchema.parse(body)

    const block = await prisma.articleBlock.findUnique({
      where: { id: blockId },
    })

    if (!block || block.articleId !== articleId) {
      return NextResponse.json({ error: 'Block not found' }, { status: 404 })
    }

    let dataPayload: Prisma.InputJsonValue | undefined
    if (validated.data !== undefined) {
      const effectiveType = validated.type ?? block.type
      const parsed = safeParseArticleBlockData(effectiveType, validated.data)
      if (!parsed.success) {
        return NextResponse.json({ error: 'Invalid block data', issues: parsed.issues }, { status: 400 })
      }
      try {
        dataPayload = JSON.parse(JSON.stringify(parsed.data)) as Prisma.InputJsonValue
      } catch {
        return NextResponse.json(
          { error: 'Block data must be JSON-serializable' },
          { status: 400 }
        )
      }
    }

    const hasData = validated.data !== undefined
    const hasType = validated.type != null
    const hasOrder = validated.order !== undefined

    if (!hasData && !hasType && !hasOrder) {
      // Corps `{}` (ex. `JSON.stringify({ data: undefined })`) — pas de MàJ possible.
      return NextResponse.json({ block, noOp: true as const })
    }

    if (hasType && validated.type === ArticleBlockType.IMAGE) {
      return NextResponse.json(
        {
          error: 'Le bloc Image n\'est plus disponible. Passez en Carrousel (même pour une seule image).',
        },
        { status: 400 }
      )
    }

    const targetLocale: Locale =
      validated.locale && isValidLocale(validated.locale) ? validated.locale : defaultLocale

    // GET admin fusionne `block.i18n[locale].data` puis `block.data` : il faut persister
    // le JSON dans `article_block_i18n` pour la locale, et le canonique `article_blocks.data`
    // uniquement pour la locale par défaut (repli côté public / autres locales).
    await prisma.$transaction(async (tx) => {
      if (hasData) {
        await tx.articleBlockI18n.upsert({
          where: {
            blockId_locale: { blockId, locale: targetLocale },
          },
          create: {
            blockId,
            locale: targetLocale,
            data: dataPayload!,
            translationStatus: TranslationStatus.ORIGINAL,
          },
          update: {
            data: dataPayload!,
          },
        })
      }

      const blockData: {
        type?: ArticleBlockType
        data?: Prisma.InputJsonValue
        order?: number
      } = {}
      if (hasType) {
        blockData.type = validated.type
      }
      if (hasOrder) {
        blockData.order = validated.order
      }
      if (hasData && targetLocale === defaultLocale) {
        blockData.data = dataPayload!
      }
      if (Object.keys(blockData).length > 0) {
        await tx.articleBlock.update({
          where: { id: blockId },
          data: blockData,
        })
      }
    })

    const updated = await prisma.articleBlock.findUnique({
      where: { id: blockId },
    })
    return NextResponse.json({ block: updated })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating block:', error)
    return NextResponse.json(adminRouteErrorBody(error), { status: 500 })
  }
}

// DELETE /api/admin/articles/[id]/blocks/[blockId]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string; blockId: string } | Promise<{ id: string; blockId: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id: articleId, blockId } = await awaitRouteParams(params)

    const block = await prisma.articleBlock.findUnique({
      where: { id: blockId },
    })

    if (!block || block.articleId !== articleId) {
      return NextResponse.json({ error: 'Block not found' }, { status: 404 })
    }

    await prisma.articleBlock.delete({
      where: { id: blockId },
    })

    return NextResponse.json({ message: 'Block deleted' })
  } catch (error) {
    console.error('Error deleting block:', error)
    return NextResponse.json(adminRouteErrorBody(error), { status: 500 })
  }
}









