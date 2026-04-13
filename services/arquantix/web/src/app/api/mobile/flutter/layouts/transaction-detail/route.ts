import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

/**
 * GET /api/mobile/flutter/layouts/transaction-detail
 * API publique pour l'app Flutter: retourne le layout "Transaction details" stocke en base.
 */
export async function GET() {
  try {
    const chapter = await prisma.dsComponentChapter.findUnique({
      where: { slug: 'component_ds_flutter' },
      select: { id: true },
    })

    if (!chapter) {
      return NextResponse.json({ error: 'Chapter not found' }, { status: 404 })
    }

    const component = await prisma.dsComponent.findUnique({
      where: {
        chapterId_slug: {
          chapterId: chapter.id,
          slug: 'transaction_detail_layout',
        },
      },
      select: {
        id: true,
        slug: true,
        name: true,
        schemaJson: true,
      },
    })

    if (!component) {
      return NextResponse.json({ error: 'Transaction detail layout not found' }, { status: 404 })
    }

    return NextResponse.json(
      {
        layout: component.schemaJson as Record<string, unknown> | null,
        meta: {
          id: component.id,
          slug: component.slug,
          name: component.name,
        },
      },
      {
        headers: {
          'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
          Pragma: 'no-cache',
          Expires: '0',
        },
      }
    )
  } catch (error) {
    console.error('[api/mobile/flutter/layouts/transaction-detail]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
