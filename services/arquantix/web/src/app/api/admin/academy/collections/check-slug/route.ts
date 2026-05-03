import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// GET /api/admin/academy/collections/check-slug?slug=...
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const slug = searchParams.get('slug')

    if (!slug) {
      return NextResponse.json({ error: 'Slug parameter is required' }, { status: 400 })
    }

    const existing = await prisma.academyCollection.findUnique({
      where: { slug },
    })

    return NextResponse.json({ exists: !!existing })
  } catch (error) {
    console.error('Error checking academy collection slug:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
