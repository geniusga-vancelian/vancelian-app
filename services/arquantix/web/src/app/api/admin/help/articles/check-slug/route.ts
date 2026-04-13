import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// GET /api/admin/help/articles/check-slug?slug=...&categoryId=...
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const slug = searchParams.get('slug')
    const categoryId = searchParams.get('categoryId')

    if (!slug || !categoryId) {
      return NextResponse.json(
        { error: 'Slug and categoryId parameters are required' },
        { status: 400 }
      )
    }

    const existing = await prisma.helpArticle.findFirst({
      where: {
        categoryId,
        slug,
      },
    })

    return NextResponse.json({ exists: !!existing })
  } catch (error) {
    console.error('Error checking slug:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

