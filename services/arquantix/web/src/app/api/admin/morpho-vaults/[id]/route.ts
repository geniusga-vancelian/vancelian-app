import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { updateMorphoVaultSchema } from '@/lib/portal/morphoVaultValidation'
import { prisma } from '@/lib/prisma'

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> | { id: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const resolved = await Promise.resolve(params)
    const id = resolved.id?.trim()
    if (!id) {
      return NextResponse.json({ error: 'Invalid id' }, { status: 400 })
    }

    const body = await request.json()
    const parsed = updateMorphoVaultSchema.parse(body)

    const existing = await prisma.portalMorphoVaultConfig.findUnique({ where: { id } })
    if (!existing) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    const updated = await prisma.portalMorphoVaultConfig.update({
      where: { id },
      data: {
        ...(parsed.integrationMode !== undefined ? { integrationMode: parsed.integrationMode } : {}),
        ...(parsed.privyVaultId !== undefined
          ? { privyVaultId: parsed.privyVaultId?.trim() || null }
          : {}),
        ...(parsed.label !== undefined ? { label: parsed.label?.trim() || null } : {}),
        ...(parsed.description !== undefined ? { description: parsed.description?.trim() || null } : {}),
        ...(parsed.curator !== undefined ? { curator: parsed.curator?.trim() || null } : {}),
        ...(parsed.sortOrder !== undefined ? { sortOrder: parsed.sortOrder } : {}),
        ...(parsed.isPublished !== undefined ? { isPublished: parsed.isPublished } : {}),
      },
    })

    return NextResponse.json({ vault: updated })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request data', issues: error.issues }, { status: 400 })
    }
    console.error('[api/admin/morpho-vaults/[id] PUT]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> | { id: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const resolved = await Promise.resolve(params)
    const id = resolved.id?.trim()
    if (!id) {
      return NextResponse.json({ error: 'Invalid id' }, { status: 400 })
    }

    await prisma.portalMorphoVaultConfig.delete({ where: { id } })
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('[api/admin/morpho-vaults/[id] DELETE]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
