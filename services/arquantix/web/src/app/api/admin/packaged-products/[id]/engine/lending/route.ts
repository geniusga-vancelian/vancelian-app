import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

function isUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s)
}

/**
 * Délie le lending_pool_product du packaged product (statut lending = draft uniquement).
 */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const packagedId = params?.id?.trim()
    if (!packagedId || !isUuid(packagedId)) {
      return NextResponse.json({ error: 'Identifiant packaged product invalide' }, { status: 400 })
    }

    const pp = await prisma.packagedProduct.findUnique({
      where: { id: packagedId },
      include: {
        lendingPoolProduct: {
          select: { id: true, status: true },
        },
      },
    })

    if (!pp?.lendingPoolProduct) {
      return NextResponse.json({ error: 'Aucun produit lending lié.' }, { status: 404 })
    }

    if (pp.lendingPoolProduct.status !== 'draft') {
      return NextResponse.json(
        {
          error:
            'Déliaison impossible : le produit lending n’est plus en brouillon (statut différent de « draft »).',
          code: 'UNLINK_NOT_ALLOWED',
        },
        { status: 409 }
      )
    }

    await prisma.$transaction([
      prisma.lendingPoolProducts.update({
        where: { id: pp.lendingPoolProduct.id },
        data: { packagedProductId: null },
      }),
      prisma.packagedProduct.update({
        where: { id: packagedId },
        data: {
          engineType: null,
          engineReferenceId: null,
        },
      }),
    ])

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('[engine/lending DELETE]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
