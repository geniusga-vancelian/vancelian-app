import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { createLendingFromPackagedBodySchema } from '@/lib/admin/packagedEngineSchemas'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { buildBackendUrl } from '@/lib/backend'

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
    const body = createLendingFromPackagedBodySchema.parse(raw)

    const pp = await prisma.packagedProduct.findUnique({
      where: { id: packagedId },
      include: { lendingPoolProduct: { select: { id: true } } },
    })

    if (!pp) {
      return NextResponse.json({ error: 'Packaged product introuvable' }, { status: 404 })
    }

    if (pp.productType !== 'EXCLUSIVE_OFFER') {
      return NextResponse.json(
        {
          error:
            'Le moteur lending est réservé aux produits packagés de type « Offre exclusive » (EXCLUSIVE_OFFER).',
          code: 'PRODUCT_TYPE_INCOMPATIBLE',
        },
        { status: 422 }
      )
    }

    if (pp.lendingPoolProduct) {
      return NextResponse.json(
        { error: 'Un produit lending est déjà lié à ce packaged product.', code: 'ALREADY_LINKED' },
        { status: 409 }
      )
    }

    if (pp.engineReferenceId || pp.engineType === 'LENDING') {
      return NextResponse.json(
        { error: 'Le registre indique déjà un moteur ; synchronisez ou déliez avant création.' },
        { status: 409 }
      )
    }

    const payload = {
      packaged_product_id: packagedId,
      borrower_client_id: body.borrower_client_id,
      asset: body.asset,
      target_size: body.target_size,
      title: body.title ?? '',
      supply_apr_bps: body.supply_apr_bps,
      borrow_apr_bps: body.borrow_apr_bps,
      min_ticket: body.min_ticket ?? null,
      max_ticket: body.max_ticket ?? null,
    }

    const res = await fetch(buildBackendUrl('/api/lending/products/create-from-packaged-product'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    const text = await res.text()
    let data: Record<string, unknown>
    try {
      data = JSON.parse(text) as Record<string, unknown>
    } catch {
      return NextResponse.json(
        { error: 'Réponse backend invalide', detail: text.slice(0, 200) },
        { status: 502 }
      )
    }

    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Données invalides', issues: error.issues }, { status: 400 })
    }
    console.error('[engine/lending/create POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
