import { NextRequest, NextResponse } from 'next/server'
import { PackagedEngineType } from '@prisma/client'
import { z } from 'zod'

import { linkLendingBodySchema } from '@/lib/admin/packagedEngineSchemas'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

function isUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s)
}

export async function POST(
  request: NextRequest,
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

    const raw = await request.json()
    const { lending_product_id } = linkLendingBodySchema.parse(raw)

    await prisma.$transaction(async (tx) => {
      const pp = await tx.packagedProduct.findUnique({
        where: { id: packagedId },
        include: { lendingPoolProduct: { select: { id: true } } },
      })

      if (!pp) {
        throw Object.assign(new Error('NOT_FOUND'), { code: 404 })
      }

      if (pp.productType !== 'EXCLUSIVE_OFFER') {
        throw Object.assign(new Error('PRODUCT_TYPE_INCOMPATIBLE'), { code: 422 })
      }

      if (pp.lendingPoolProduct && pp.lendingPoolProduct.id !== lending_product_id) {
        throw Object.assign(new Error('PACKAGED_ALREADY_LINKED'), { code: 409 })
      }

      if (pp.engineType === 'LENDING' && pp.engineReferenceId && pp.engineReferenceId !== lending_product_id) {
        throw Object.assign(new Error('REGISTRY_ENGINE_CONFLICT'), { code: 409 })
      }

      const lpp = await tx.lendingPoolProducts.findUnique({
        where: { id: lending_product_id },
      })

      if (!lpp) {
        throw Object.assign(new Error('LENDING_NOT_FOUND'), { code: 404 })
      }

      if (lpp.packagedProductId && lpp.packagedProductId !== packagedId) {
        throw Object.assign(new Error('LENDING_LINKED_ELSEWHERE'), { code: 409 })
      }

      if (lpp.packagedProductId === packagedId) {
        return
      }

      await tx.lendingPoolProducts.update({
        where: { id: lending_product_id },
        data: { packagedProductId: packagedId },
      })

      await tx.packagedProduct.update({
        where: { id: packagedId },
        data: {
          engineType: PackagedEngineType.LENDING,
          engineReferenceId: lending_product_id,
        },
      })
    })

    const detail = await prisma.packagedProduct.findUnique({
      where: { id: packagedId },
      include: {
        lendingPoolProduct: {
          select: {
            id: true,
            lendingPoolId: true,
            title: true,
            status: true,
            asset: true,
            borrowerClientId: true,
            targetSize: true,
            currentRaised: true,
            supplyAprBps: true,
          },
        },
      },
    })

    return NextResponse.json({ success: true, packagedProduct: detail })
  } catch (error: unknown) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Données invalides', issues: error.issues }, { status: 400 })
    }
    const e = error as { code?: number; message?: string }
    if (e.code === 404) {
      return NextResponse.json({ error: 'Ressource introuvable' }, { status: 404 })
    }
    if (e.message === 'PRODUCT_TYPE_INCOMPATIBLE') {
      return NextResponse.json(
        {
          error:
            'Liaison lending réservée aux produits EXCLUSIVE_OFFER.',
          code: 'PRODUCT_TYPE_INCOMPATIBLE',
        },
        { status: 422 }
      )
    }
    if (e.message === 'PACKAGED_ALREADY_LINKED' || e.message === 'REGISTRY_ENGINE_CONFLICT') {
      return NextResponse.json(
        { error: 'Ce packaged product a déjà un autre moteur lending.', code: 'PACKAGED_CONFLICT' },
        { status: 409 }
      )
    }
    if (e.message === 'LENDING_NOT_FOUND') {
      return NextResponse.json({ error: 'Produit lending introuvable.' }, { status: 404 })
    }
    if (e.message === 'LENDING_LINKED_ELSEWHERE') {
      return NextResponse.json(
        {
          error: 'Ce produit lending est déjà lié à un autre packaged product.',
          code: 'LENDING_TAKEN',
        },
        { status: 409 }
      )
    }
    console.error('[engine/lending/link POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
