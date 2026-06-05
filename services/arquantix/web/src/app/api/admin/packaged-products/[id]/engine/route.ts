import { NextRequest, NextResponse } from 'next/server'

import { fetchVaultEngineSnapshot } from '@/lib/admin/platformVaultEngine'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { buildBackendUrl } from '@/lib/backend'

function isUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s)
}

type LppRow = {
  id: string
  lendingPoolId: string
  title: string
  status: string
  asset: string
  borrowerClientId: string
  targetSize: { toString(): string }
  currentRaised: { toString(): string }
  supplyAprBps: { toString(): string }
  projectId: string | null
  packagedProductId: string | null
}

function serializeLpp(lpp: LppRow | null) {
  if (!lpp) return null
  return {
    id: lpp.id,
    lendingPoolId: lpp.lendingPoolId,
    title: lpp.title,
    status: lpp.status,
    asset: lpp.asset,
    borrowerClientId: lpp.borrowerClientId,
    targetSize: String(lpp.targetSize),
    currentRaised: String(lpp.currentRaised),
    supplyAprBps: String(lpp.supplyAprBps),
    projectId: lpp.projectId,
    packagedProductId: lpp.packagedProductId,
  }
}

export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const id = params?.id?.trim()
    if (!id || !isUuid(id)) {
      return NextResponse.json({ error: 'Identifiant packaged product invalide' }, { status: 400 })
    }

    const pp = await prisma.packagedProduct.findUnique({
      where: { id },
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
            projectId: true,
            packagedProductId: true,
          },
        },
      },
    })

    if (!pp) {
      return NextResponse.json({ error: 'Packaged product introuvable' }, { status: 404 })
    }

    let lendingSnapshot: Record<string, unknown> | null = null
    let vaultEngineSnapshot: Record<string, unknown> | null = null
    const ref = pp.engineReferenceId
    if (pp.engineType === 'LENDING' && ref) {
      try {
        const res = await fetch(buildBackendUrl(`/api/lending/products/${ref}`), {
          cache: 'no-store',
        })
        if (res.ok) {
          lendingSnapshot = (await res.json()) as Record<string, unknown>
        }
      } catch {
        lendingSnapshot = null
      }
    }
    if (pp.engineType === 'VAULT_ENGINE' && ref?.trim()) {
      const snap = await fetchVaultEngineSnapshot(ref.trim())
      vaultEngineSnapshot = snap ? (snap as unknown as Record<string, unknown>) : null
    }

    return NextResponse.json({
      packagedProductId: pp.id,
      productType: pp.productType,
      engineType: pp.engineType,
      engineReferenceId: pp.engineReferenceId,
      lendingPoolProduct: serializeLpp(pp.lendingPoolProduct),
      lendingSnapshot,
      vaultEngineSnapshot,
    })
  } catch (error) {
    console.error('[packaged-products/engine GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
