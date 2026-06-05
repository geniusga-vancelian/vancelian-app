import { NextRequest, NextResponse } from 'next/server'
import { PackagedEngineType } from '@prisma/client'
import { z } from 'zod'

import { linkVaultBodySchema } from '@/lib/admin/packagedEngineSchemas'
import {
  isVaultEngineEligibleProductType,
  resolvePlatformVaultAdminRow,
} from '@/lib/admin/platformVaultEngine'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

function isUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s)
}

export async function POST(
  request: NextRequest,
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

    const raw = await request.json()
    const { portal_config_id } = linkVaultBodySchema.parse(raw)

    const vaultRow = await resolvePlatformVaultAdminRow(portal_config_id)
    if (!vaultRow) {
      return NextResponse.json({ error: 'Vault plateforme introuvable.' }, { status: 404 })
    }

    await prisma.$transaction(async (tx) => {
      const pp = await tx.packagedProduct.findUnique({
        where: { id: packagedId },
        include: { lendingPoolProduct: { select: { id: true } } },
      })

      if (!pp) {
        throw Object.assign(new Error('NOT_FOUND'), { code: 404 })
      }

      if (!isVaultEngineEligibleProductType(pp.productType)) {
        throw Object.assign(new Error('PRODUCT_TYPE_INCOMPATIBLE'), { code: 422 })
      }

      if (pp.lendingPoolProduct) {
        throw Object.assign(new Error('LENDING_STILL_LINKED'), { code: 409 })
      }

      if (
        pp.engineType === 'LENDING' &&
        pp.engineReferenceId &&
        pp.engineReferenceId !== portal_config_id
      ) {
        throw Object.assign(new Error('REGISTRY_ENGINE_CONFLICT'), { code: 409 })
      }

      await tx.packagedProduct.update({
        where: { id: packagedId },
        data: {
          engineType: PackagedEngineType.VAULT_ENGINE,
          engineReferenceId: portal_config_id,
        },
      })
    })

    const detail = await prisma.packagedProduct.findUnique({
      where: { id: packagedId },
      select: {
        id: true,
        engineType: true,
        engineReferenceId: true,
        productType: true,
      },
    })

    return NextResponse.json({
      success: true,
      packagedProduct: detail,
      linkedVault: vaultRow,
    })
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
          error: 'Liaison vault réservée aux types VAULT_SIMPLE et EXCLUSIVE_OFFER.',
          code: 'PRODUCT_TYPE_INCOMPATIBLE',
        },
        { status: 422 },
      )
    }
    if (e.message === 'LENDING_STILL_LINKED' || e.message === 'REGISTRY_ENGINE_CONFLICT') {
      return NextResponse.json(
        {
          error:
            'Déliez d’abord le moteur lending existant avant de connecter un vault plateforme.',
          code: 'ENGINE_CONFLICT',
        },
        { status: 409 },
      )
    }
    console.error('[engine/vault/link POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
