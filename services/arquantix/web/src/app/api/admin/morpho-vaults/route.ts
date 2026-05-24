import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { fetchMorphoVaultsByAddresses } from '@/lib/portal/morphoGraphql'
import { mergeMorphoVaultConfigWithGraphql } from '@/lib/portal/morphoVaultFormat'
import { listPortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import {
  createMorphoVaultSchema,
  normalizeCreateMorphoVaultInput,
} from '@/lib/portal/morphoVaultValidation'
import { prisma } from '@/lib/prisma'

export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const configs = await listPortalMorphoVaultConfigs()
    const gqlRows = await fetchMorphoVaultsByAddresses({
      addresses: configs.map((row) => row.vaultAddress),
    })
    const gqlByAddress = new Map(gqlRows.map((row) => [row.address.toLowerCase(), row]))

    return NextResponse.json({
      vaults: configs.map((config) =>
        mergeMorphoVaultConfigWithGraphql(config, gqlByAddress.get(config.vaultAddress.toLowerCase())),
      ),
    })
  } catch (error) {
    console.error('[api/admin/morpho-vaults GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const parsed = createMorphoVaultSchema.parse(body)
    const data = normalizeCreateMorphoVaultInput(parsed)

    const created = await prisma.portalMorphoVaultConfig.create({ data })
    return NextResponse.json({ vault: created }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request data', issues: error.issues }, { status: 400 })
    }
    console.error('[api/admin/morpho-vaults POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
