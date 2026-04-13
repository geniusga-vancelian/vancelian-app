import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'
const VAULT_DEFAULT_LOCALE = 'fr'

const reorderSchema = z.object({
  slug: z.string().min(1),
  direction: z.enum(['up', 'down']),
})

function getMetaFromData(data: unknown): { investmentTypeSlug: string | null; sortOrder: number } {
  if (data == null || typeof data !== 'object') return { investmentTypeSlug: null, sortOrder: 999 }
  const o = data as Record<string, unknown>
  let investmentTypeSlug: string | null = null
  if (typeof o.investmentTypeSlug === 'string' && o.investmentTypeSlug.trim()) {
    investmentTypeSlug = o.investmentTypeSlug.trim()
  }
  if (!investmentTypeSlug && o.config != null && typeof o.config === 'object') {
    const cfg = o.config as Record<string, unknown>
    if (typeof cfg.investmentTypeSlug === 'string' && cfg.investmentTypeSlug.trim()) {
      investmentTypeSlug = cfg.investmentTypeSlug.trim()
    }
  }
  const sortOrder = typeof o.sortOrder === 'number' ? o.sortOrder : 999
  return { investmentTypeSlug, sortOrder }
}

function normalizeCategory(s: string | null): string {
  return (s ?? '').trim() || '__none__'
}

/** POST /api/admin/vault-reorder — Réordonne un vault dans sa catégorie (évite conflit avec vaults/[slug]). */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const parsed = reorderSchema.parse(body)
    const slug = parsed.slug.trim()
    const direction = parsed.direction

    const allPages = await prisma.page.findMany({
      where: { template: VAULT_TEMPLATE_DB },
      orderBy: { slug: 'asc' },
      include: {
        sections: {
          where: { key: VAULT_SECTION_KEY },
          include: {
            contents: {
              where: {
                locale: VAULT_DEFAULT_LOCALE,
                status: ContentStatus.DRAFT,
              },
              take: 1,
            },
          },
          take: 1,
        },
      },
    })

    const withMeta = allPages.map((p) => {
      const data = p.sections[0]?.contents[0]?.data
      const meta = getMetaFromData(data)
      return { page: p, ...meta, data }
    })

    const currentIndex = withMeta.findIndex((w) => w.page.slug === slug)
    if (currentIndex < 0) {
      return NextResponse.json({ error: 'Vault not found' }, { status: 404 })
    }

    const current = withMeta[currentIndex]
    const category = normalizeCategory(current.investmentTypeSlug)
    const sameCategory = withMeta
      .map((w, i) => ({ ...w, index: i }))
      .filter((w) => normalizeCategory(w.investmentTypeSlug) === category)
      .sort((a, b) => {
        if (a.sortOrder !== b.sortOrder) return a.sortOrder - b.sortOrder
        return (a.page.slug ?? '').localeCompare(b.page.slug ?? '')
      })

    const posInCategory = sameCategory.findIndex((s) => s.page.slug === slug)
    if (posInCategory < 0) {
      return NextResponse.json(
        {
          error: 'Vault not in category',
          detail: `slug=${slug} category=${category} sameCategoryCount=${sameCategory.length}`,
        },
        { status: 400 }
      )
    }

    const targetPos = direction === 'up' ? posInCategory - 1 : posInCategory + 1
    if (targetPos < 0 || targetPos >= sameCategory.length) {
      return NextResponse.json(
        { error: 'Cannot move further', detail: `pos=${posInCategory} target=${targetPos} len=${sameCategory.length}` },
        { status: 400 }
      )
    }

    const reordered = [...sameCategory]
    const tmp = reordered[posInCategory]
    reordered[posInCategory] = reordered[targetPos]
    reordered[targetPos] = tmp

    const statuses: ContentStatus[] = [ContentStatus.DRAFT, ContentStatus.PUBLISHED]
    for (let i = 0; i < reordered.length; i++) {
      const item = reordered[i]
      const section = item.page.sections[0]
      if (!section) continue

      const data = (item.data ?? {}) as Record<string, unknown>
      const updatedData = { ...data, sortOrder: i }

      for (const status of statuses) {
        await prisma.sectionContent.upsert({
          where: {
            sectionId_locale_status: {
              sectionId: section.id,
              locale: VAULT_DEFAULT_LOCALE,
              status,
            },
          },
          update: { data: updatedData, updatedByUserId: session.userId },
          create: {
            sectionId: section.id,
            locale: VAULT_DEFAULT_LOCALE,
            status,
            data: updatedData,
            updatedByUserId: session.userId,
          },
        })
      }
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Données invalides', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error reordering vault:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
