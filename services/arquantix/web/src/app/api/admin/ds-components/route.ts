import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

/** GET /api/admin/ds-components — Liste des chapitres et composants DS (admin). */
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const chapters = await prisma.dsComponentChapter.findMany({
      orderBy: { order: 'asc' },
      include: {
        components: true,
      },
    })

    return NextResponse.json({ chapters })
  } catch (e) {
    console.error('[api/admin/ds-components]', e)
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Internal error' },
      { status: 500 }
    )
  }
}
