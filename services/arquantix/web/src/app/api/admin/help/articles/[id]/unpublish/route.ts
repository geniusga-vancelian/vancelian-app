import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// POST /api/admin/help/articles/[id]/unpublish
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const article = await prisma.helpArticle.update({
      where: { id: params.id },
      data: {
        status: 'DRAFT',
      },
    })

    return NextResponse.json({ article })
  } catch (error) {
    console.error('Error unpublishing article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









