/**
 * API pour la configuration des modules d'un produit Portfolio Engine.
 * GET: récupère la config (modules)
 * PUT: met à jour la config (modules)
 */
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import type { Prisma } from '@prisma/client'

const moduleSchema = z.object({
  id: z.string(),
  type: z.string(),
  enabled: z.boolean().default(true),
  content: z.any().default({}), // Objets imbriqués (rows, items, etc.)
})

const configSchema = z.object({
  headerMediaId: z.string().nullable().optional(),
  detailMediaId: z.string().nullable().optional(),
  modules: z.array(moduleSchema).optional(),
  sortOrder: z.number().int().min(0).optional(),
  isPublished: z.boolean().optional(),
})

function normalizeProductCode(code: string | undefined): string {
  if (code == null || typeof code !== 'string') return ''
  return code.trim()
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ productCode: string }> | { productCode: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const resolved = await Promise.resolve(params)
    const productCode = normalizeProductCode(resolved?.productCode)
    if (!productCode) {
      return NextResponse.json({ error: 'Invalid product_code' }, { status: 400 })
    }

    const config = await prisma.portfolioProductConfig.findUnique({
      where: { productCode },
    })

    if (!config) {
      return NextResponse.json({ headerMediaId: null, detailMediaId: null, modules: [], sortOrder: 999, isPublished: false })
    }

    const modules = Array.isArray(config.modules) ? config.modules : []
    return NextResponse.json({
      headerMediaId: config.headerMediaId ?? null,
      detailMediaId: config.detailMediaId ?? null,
      modules,
      sortOrder: config.sortOrder ?? 999,
      isPublished: config.isPublished ?? false,
    })
  } catch (error) {
    console.error('[api/admin/portfolio-engine/products/config GET]', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ productCode: string }> | { productCode: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const resolved = await Promise.resolve(params)
    const productCode = normalizeProductCode(resolved?.productCode)
    if (!productCode) {
      return NextResponse.json({ error: 'Invalid product_code' }, { status: 400 })
    }

    const body = await request.json()
    const parsed = configSchema.parse(body)

    const updateData: Record<string, unknown> = {}
    const createData: Record<string, unknown> = { productCode }

    if (parsed.headerMediaId !== undefined) {
      updateData.headerMediaId = parsed.headerMediaId ?? null
      createData.headerMediaId = parsed.headerMediaId ?? null
    }
    if (parsed.detailMediaId !== undefined) {
      updateData.detailMediaId = parsed.detailMediaId ?? null
      createData.detailMediaId = parsed.detailMediaId ?? null
    }
    if (parsed.modules !== undefined) {
      const modulesJson = JSON.parse(JSON.stringify(parsed.modules))
      updateData.modules = modulesJson
      createData.modules = modulesJson
    }
    if (parsed.sortOrder !== undefined) {
      updateData.sortOrder = parsed.sortOrder
      createData.sortOrder = parsed.sortOrder
    } else {
      createData.sortOrder = 999
    }
    if (parsed.isPublished !== undefined) {
      updateData.isPublished = parsed.isPublished
      createData.isPublished = parsed.isPublished
    } else {
      createData.isPublished = false
    }

    await prisma.portfolioProductConfig.upsert({
      where: { productCode },
      update: updateData as Prisma.PortfolioProductConfigUpdateInput,
      create: createData as Prisma.PortfolioProductConfigUncheckedCreateInput,
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/portfolio-engine/products/config PUT]', err.message, err.stack)
    return NextResponse.json(
      {
        error: 'Internal server error',
        detail: process.env.NODE_ENV === 'development' ? err.message : undefined,
      },
      { status: 500 }
    )
  }
}
