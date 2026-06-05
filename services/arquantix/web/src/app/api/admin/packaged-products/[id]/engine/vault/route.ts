import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

function isUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s)
}

/**
 * Délie le vault plateforme du packaged product (moteur VAULT_ENGINE).
 */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: { id: string } },
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
      select: { id: true, engineType: true, engineReferenceId: true },
    })

    if (!pp || pp.engineType !== 'VAULT_ENGINE' || !pp.engineReferenceId?.trim()) {
      return NextResponse.json({ error: 'Aucun vault plateforme lié.' }, { status: 404 })
    }

    await prisma.packagedProduct.update({
      where: { id: packagedId },
      data: {
        engineType: null,
        engineReferenceId: null,
      },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('[engine/vault DELETE]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
