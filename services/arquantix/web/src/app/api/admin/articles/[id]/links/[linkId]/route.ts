import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// DELETE /api/admin/articles/[id]/links/[linkId]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string; linkId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const deleted = await prisma.articleLink.deleteMany({
      where: {
        id: params.linkId,
        articleId: params.id,
      },
    })

    if (deleted.count === 0) {
      return NextResponse.json({ error: 'Link not found' }, { status: 404 })
    }

    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error('Error deleting article link:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
