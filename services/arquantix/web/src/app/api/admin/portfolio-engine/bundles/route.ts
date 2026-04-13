/**
 * POST /api/admin/portfolio-engine/bundles
 *
 * Thin proxy to FastAPI Bundle Engine v1.
 *
 * 1. Forwards the payload to POST /api/portfolio-engine/admin/bundles
 * 2. On success, performs a best-effort Prisma UI config upsert
 *    (non-atomic with the FastAPI transaction).
 * 3. Returns the FastAPI response with an optional warning if Prisma failed.
 *
 * Business consistency lives in FastAPI only.
 */
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { prisma } from '@/lib/prisma'
import type { Prisma } from '@prisma/client'

const allocationSchema = z.object({
  instrumentId: z.string().uuid(),
  instrumentCode: z.string(),
  assetSymbol: z.string(),
  targetWeight: z.number().min(0).max(1),
})

const createBundleSchema = z.object({
  name: z.string().min(1).max(255),
  productCode: z.string().min(1).max(100),
  description: z.string().optional().default(''),
  riskLabel: z.enum(['low', 'moderate', 'high', 'very_high']).optional().default('high'),
  baseCurrency: z.string().optional().default('USD'),
  allocations: z.array(allocationSchema).min(1),
  availableRebalanceFrequencies: z.array(z.string()).optional().default(['weekly', 'monthly', 'quarterly']),
})

/** FastAPI peut renvoyer detail: string | { loc, msg }[] — normaliser pour l’UI. */
function formatFastApiDetail(detail: unknown): string {
  if (detail == null) return ''
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === 'object' && 'msg' in item) {
        const loc = 'loc' in item && Array.isArray((item as { loc?: unknown }).loc)
          ? (item as { loc: unknown[] }).loc.join('.')
          : ''
        return loc ? `${loc}: ${(item as { msg: string }).msg}` : String((item as { msg: string }).msg)
      }
      return JSON.stringify(item)
    })
    return parts.join(' ; ')
  }
  if (typeof detail === 'object') return JSON.stringify(detail)
  return String(detail)
}

/**
 * Les poids viennent de pourcentages /100 en JS — normaliser pour que la somme = 1
 * (évite les écarts type 0.999… qui peuvent faire échouer la validation côté API).
 */
function normalizeTargetWeights(
  allocations: { instrumentId: string; instrumentCode: string; assetSymbol: string; targetWeight: number }[]
) {
  const raw = allocations.map((a) => Math.max(0, a.targetWeight))
  const sum = raw.reduce((s, w) => s + w, 0)
  if (sum <= 0) return allocations
  return allocations.map((a, i) => ({
    ...a,
    targetWeight: raw[i]! / sum,
  }))
}

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const parsed = createBundleSchema.parse(body)
    const allocationsNorm = normalizeTargetWeights(parsed.allocations)

    // ── 1. Forward to FastAPI Bundle Engine ──
    const fastapiPayload = {
      name: parsed.name,
      product_code: parsed.productCode,
      description: parsed.description || undefined,
      risk_label: parsed.riskLabel,
      base_currency: parsed.baseCurrency,
      is_public: false,
      entry_asset_default: 'USDC',
      entry_assets_allowed: ['USDC'],
      allocations: allocationsNorm.map((a) => ({
        instrument_id: a.instrumentId,
        target_weight: a.targetWeight,
      })),
      available_rebalance_frequencies: parsed.availableRebalanceFrequencies,
      metadata: {
        short_description: parsed.description || parsed.name,
      },
    }

    const url = buildBackendUrl('/api/portfolio-engine/admin/bundles')
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Actor-Type': 'admin',
        'X-Actor-Roles': 'admin',
      },
      body: JSON.stringify(fastapiPayload),
      signal: AbortSignal.timeout(15000),
    })

    const data = await res.json().catch(() => ({}))

    if (!res.ok) {
      const apiMessage = formatFastApiDetail(data.detail) || 'Bundle creation failed in backend'
      return NextResponse.json(
        {
          error: apiMessage,
          detail: data,
        },
        { status: res.status },
      )
    }

    // ── 2. Best-effort Prisma UI config upsert ──
    let uiConfigWarning: string | undefined
    try {
      const greys = ['#374151', '#6B7280', '#9CA3AF', '#D1D5DB', '#E5E7EB', '#CBD5E1']
      const slices = allocationsNorm.map((a, i) => ({
        label: a.assetSymbol,
        percentage: Math.round(a.targetWeight * 10000) / 100,
        colorHex: greys[i % greys.length],
      }))

      const requiredModules = [
        {
          id: crypto.randomUUID(),
          type: 'TitlePage',
          enabled: true,
          content: { title: parsed.name, subtitle: '' },
        },
        {
          id: crypto.randomUUID(),
          type: 'PerformanceChart',
          enabled: true,
          content: { title: 'Performance' },
        },
        {
          id: crypto.randomUUID(),
          type: 'AllocationModule',
          enabled: true,
          content: {
            title: 'Allocation',
            introText: '',
            size: 'large',
            slices,
          },
        },
      ]

      const modulesJson = requiredModules as unknown as Prisma.InputJsonValue
      await prisma.portfolioProductConfig.upsert({
        where: { productCode: parsed.productCode },
        update: { modules: modulesJson },
        create: {
          productCode: parsed.productCode,
          modules: modulesJson,
        },
      })
    } catch (prismaError) {
      const msg = prismaError instanceof Error ? prismaError.message : String(prismaError)
      console.error('[create-bundle] Prisma UI config upsert failed (non-fatal):', msg)
      uiConfigWarning =
        'Bundle created successfully in backend, but UI module configuration failed. ' +
        'The bundle exists but may need manual UI config setup.'
    }

    // ── 3. Return response ──
    return NextResponse.json(
      {
        success: true,
        productId: data.id,
        productCode: data.product_code,
        templateId: data.template_id,
        ...(uiConfigWarning ? { warning: uiConfigWarning } : {}),
      },
      { status: 201 },
    )
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Données invalides', issues: error.issues },
        { status: 400 },
      )
    }
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[create-bundle]', err.message, err.stack)
    return NextResponse.json(
      {
        error: 'Création du bundle impossible',
        detail: process.env.NODE_ENV === 'development' ? err.message : undefined,
      },
      { status: 500 },
    )
  }
}
