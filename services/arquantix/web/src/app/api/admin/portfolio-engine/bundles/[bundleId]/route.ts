/**
 * PATCH /api/admin/portfolio-engine/bundles/[bundleId]
 *   → Visibility (publish/unpublish): FastAPI first, Prisma sync.
 *
 * DELETE /api/admin/portfolio-engine/bundles/[bundleId]
 *   → Thin proxy to FastAPI Bundle Engine DELETE endpoint.
 *     Also cleans up the Prisma UI config (best-effort).
 */
import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { prisma } from '@/lib/prisma'

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ bundleId: string }> | { bundleId: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const resolved = await Promise.resolve(params)
    const bundleId = resolved?.bundleId?.trim()
    if (!bundleId) {
      return NextResponse.json({ error: 'Missing bundleId' }, { status: 400 })
    }

    const body = await request.json()
    const isPublic = body?.is_public
    if (typeof isPublic !== 'boolean') {
      return NextResponse.json({ error: 'is_public (boolean) is required' }, { status: 400 })
    }

    // ── 1. FastAPI is the source of truth ──
    const url = buildBackendUrl(`/api/portfolio-engine/admin/bundles/${bundleId}/visibility`)
    const res = await fetch(url, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-Actor-Type': 'admin',
        'X-Actor-Roles': 'admin',
      },
      body: JSON.stringify({ is_public: isPublic }),
      signal: AbortSignal.timeout(15000),
    })

    const data = await res.json().catch(() => ({}))

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail || 'Visibility update failed in backend', detail: data },
        { status: res.status },
      )
    }

    // ── 2. Sync Prisma isPublished (best-effort, 1 retry) ──
    let prismaWarning: string | undefined
    const productCode = data.product_code as string | undefined
    if (productCode) {
      let synced = false
      for (let attempt = 0; attempt < 2 && !synced; attempt++) {
        try {
          await prisma.portfolioProductConfig.update({
            where: { productCode },
            data: { isPublished: isPublic },
          })
          synced = true
        } catch (prismaError) {
          if (attempt === 0) {
            console.warn(`[visibility] Prisma sync attempt 1 failed for ${productCode}, retrying...`)
            await new Promise((r) => setTimeout(r, 300))
          } else {
            const msg = prismaError instanceof Error ? prismaError.message : String(prismaError)
            console.error('[visibility] Prisma sync failed after retry (non-fatal):', msg)
            prismaWarning =
              `Visibility updated in backend, but Prisma UI sync failed for ${productCode}. ` +
              'The admin may need to toggle again or save the config manually.'
          }
        }
      }
    }

    return NextResponse.json({
      ...data,
      ...(prismaWarning ? { warning: prismaWarning } : {}),
    })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[visibility]', err.message, err.stack)
    return NextResponse.json(
      {
        error: 'Mise à jour de la visibilité impossible',
        detail: process.env.NODE_ENV === 'development' ? err.message : undefined,
      },
      { status: 500 },
    )
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ bundleId: string }> | { bundleId: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const resolved = await Promise.resolve(params)
    const bundleId = resolved?.bundleId?.trim()
    if (!bundleId) {
      return NextResponse.json({ error: 'Missing bundleId' }, { status: 400 })
    }

    const url = buildBackendUrl(`/api/portfolio-engine/admin/bundles/${bundleId}`)
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-Actor-Type': 'admin',
        'X-Actor-Roles': 'admin',
      },
      signal: AbortSignal.timeout(15000),
    })

    const data = await res.json().catch(() => ({}))

    if (!res.ok) {
      return NextResponse.json(
        {
          error: data.detail || 'Bundle deletion failed in backend',
          detail: data,
        },
        { status: res.status },
      )
    }

    // Best-effort: delete Prisma UI config
    if (data.product_code) {
      try {
        await prisma.portfolioProductConfig.delete({
          where: { productCode: data.product_code },
        })
      } catch {
        // Config may not exist — non-fatal
      }
    }

    return NextResponse.json(data)
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[delete-bundle]', err.message, err.stack)
    return NextResponse.json(
      {
        error: 'Suppression du bundle impossible',
        detail: process.env.NODE_ENV === 'development' ? err.message : undefined,
      },
      { status: 500 },
    )
  }
}
