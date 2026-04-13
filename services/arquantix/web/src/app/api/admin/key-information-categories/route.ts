import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// GET /api/admin/key-information-categories
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const categories = await prisma.keyInformationCategory.findMany({
      orderBy: [{ sortOrder: 'asc' }, { label: 'asc' }],
    })

    return NextResponse.json({
      categories: categories.map((c) => ({
        id: c.id,
        key: c.key,
        label: c.label,
        infoTitle: c.infoTitle,
        infoContent: c.infoContent,
      })),
    })
  } catch (error) {
    console.error('Error fetching key information categories:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
