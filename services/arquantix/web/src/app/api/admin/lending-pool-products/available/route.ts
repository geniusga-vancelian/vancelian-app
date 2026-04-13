import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

/**
 * Liste les lending_pool_products sans packaged_product_id, avec recherche optionnelle.
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const q = (request.nextUrl.searchParams.get('q') ?? '').trim()
    const take = Math.min(Number(request.nextUrl.searchParams.get('limit') ?? '30') || 30, 100)

    const where =
      q.length > 0
        ? {
            packagedProductId: null,
            OR: [
              { title: { contains: q, mode: 'insensitive' as const } },
              { asset: { contains: q, mode: 'insensitive' as const } },
              ...(/^[0-9a-f-]{36}$/i.test(q) ? [{ id: q }] : []),
            ],
          }
        : { packagedProductId: null }

    const rows = await prisma.lendingPoolProducts.findMany({
      where,
      select: {
        id: true,
        title: true,
        asset: true,
        status: true,
        targetSize: true,
        currentRaised: true,
        borrowerClientId: true,
        projectId: true,
      },
      orderBy: { createdAt: 'desc' },
      take,
    })

    return NextResponse.json({ items: rows })
  } catch (error) {
    console.error('[lending-pool-products/available GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
