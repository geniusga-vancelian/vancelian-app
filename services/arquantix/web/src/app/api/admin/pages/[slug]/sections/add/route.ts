import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { getSectionType, resolveCanonicalSectionKey } from '@/lib/sections/library'
import { ContentStatus, Prisma } from '@prisma/client'
import { defaultLocale } from '@/config/locales'
import { z } from 'zod'
import {
  getCommonModuleById,
  parseCommonModulesDocument,
} from '@/lib/cms/commonModulesStorage'
import { BLOG_LIST_TEMPLATE_RENDER_CANONICAL_KEYS } from '@/lib/cms/blogListTemplateSectionPolicy'
import {
  additionUsesHeroSlot,
  HERO_SLOT_ALREADY_USED_MESSAGE_FR,
  pageHasAnyHeroSection,
} from '@/lib/sections/heroSlotPolicy'

const addSectionSchema = z.object({
  typeKey: z.string().min(1, 'Section type key is required'),
  /** Obligatoire si `typeKey` = common_module_ref */
  commonModuleId: z.string().min(1).optional(),
})

/**
 * Clé unique sur la page : si `hero` existe déjà, renvoie `hero_2`, puis `hero_3`, etc.
 */
function allocateUniqueSectionKey(existingKeys: Set<string>, baseKey: string): string {
  if (!existingKeys.has(baseKey)) return baseKey
  let n = 2
  while (existingKeys.has(`${baseKey}_${n}`)) {
    n += 1
  }
  return `${baseKey}_${n}`
}

/**
 * POST /api/admin/pages/[slug]/sections/add
 * Add a new section to a page from the section library
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = addSectionSchema.parse(body)

    const page = await prisma.page.findUnique({
      where: { slug: params.slug },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const pageSections = await prisma.section.findMany({
      where: { pageId: page.id },
      select: {
        key: true,
        order: true,
        contents: {
          where: { locale: defaultLocale },
          orderBy: { updatedAt: 'desc' },
          take: 1,
          select: { data: true },
        },
      },
      orderBy: { order: 'desc' },
    })
    const existingKeys = new Set(pageSections.map((s) => s.key))
    const nextOrder = pageSections.length > 0 ? pageSections[0].order + 1 : 0

    const gs = await prisma.globalSettings.findFirst({
      select: { commonModulesJson: true },
    })
    const commonModulesDoc = parseCommonModulesDocument(gs?.commonModulesJson ?? null)

    if (
      additionUsesHeroSlot(validated.typeKey, commonModulesDoc, validated.commonModuleId) &&
      pageHasAnyHeroSection(pageSections, commonModulesDoc)
    ) {
      return NextResponse.json({ error: HERO_SLOT_ALREADY_USED_MESSAGE_FR }, { status: 409 })
    }

    /**
     * Unicité stricte : `hero` et `hero_secondary` (un seul de chaque par page).
     * Tout autre type : clés numérotées auto (`cta_2`, `media_text_3`, …).
     */
    const UNIQUE_SECTION_KEYS = new Set(['hero', 'hero_secondary'])

    let sectionKey = validated.typeKey
    if (existingKeys.has(validated.typeKey)) {
      if (UNIQUE_SECTION_KEYS.has(validated.typeKey)) {
        return NextResponse.json(
          {
            error: `A section with key "${validated.typeKey}" already exists on this page`,
          },
          { status: 409 },
        )
      }
      sectionKey = allocateUniqueSectionKey(existingKeys, validated.typeKey)
    }

    // Get section type from library
    const sectionType = getSectionType(validated.typeKey)
    if (!sectionType) {
      return NextResponse.json(
        { error: `Unknown section type: ${validated.typeKey}` },
        { status: 400 }
      )
    }

    let contentData = sectionType.defaultData as Record<string, unknown>
    /** Pour `common_module_ref` : clé canonique du type cible (contrat liste blog). */
    let commonModuleTargetCanonical: string | null = null

    if (sectionType.key === 'common_module_ref') {
      const mid = validated.commonModuleId?.trim()
      if (!mid) {
        return NextResponse.json(
          { error: 'commonModuleId est requis pour insérer un module commun' },
          { status: 400 },
        )
      }
      const mod = getCommonModuleById(commonModulesDoc, mid)
      if (!mod) {
        return NextResponse.json(
          { error: 'Module commun introuvable (Structure du site → Zone 2)' },
          { status: 400 },
        )
      }
      commonModuleTargetCanonical =
        resolveCanonicalSectionKey(mod.sectionKey) ?? mod.sectionKey
      contentData = { commonModuleId: mid }
    }

    // Check if template allows this section type
    if (!sectionType.allowedOnTemplates.includes(page.template) && !sectionType.allowedOnTemplates.includes('default')) {
      return NextResponse.json(
        { error: `Section type "${sectionType.label}" is not allowed on template "${page.template}"` },
        { status: 400 }
      )
    }

    if (page.template === 'blog') {
      const renderCanonical =
        commonModuleTargetCanonical ??
        (resolveCanonicalSectionKey(validated.typeKey) ?? validated.typeKey)
      if (!BLOG_LIST_TEMPLATE_RENDER_CANONICAL_KEYS.has(renderCanonical)) {
        const allowed = [...BLOG_LIST_TEMPLATE_RENDER_CANONICAL_KEYS].sort().join(', ')
        return NextResponse.json(
          {
            error: `Sur le gabarit « blog », seuls les modules suivants s’affichent sur le site public : ${allowed}.`,
          },
          { status: 400 },
        )
      }
    }

    // Create section with default content (DRAFT and PUBLISHED)
    const section = await prisma.section.create({
      data: {
        pageId: page.id,
        key: sectionKey,
        order: nextOrder,
        schemaVersion: sectionType.schemaVersion,
        contents: {
          create: [
            {
              locale: defaultLocale,
              status: ContentStatus.DRAFT,
              data: contentData as Prisma.InputJsonValue,
              updatedByUserId: session.userId,
            },
            {
              locale: defaultLocale,
              status: ContentStatus.PUBLISHED,
              data: contentData as Prisma.InputJsonValue,
              updatedByUserId: session.userId,
            },
          ],
        },
      },
      include: {
        contents: {
          select: {
            id: true,
            locale: true,
            status: true,
          },
        },
      },
    })

    return NextResponse.json({ section }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error adding section:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









