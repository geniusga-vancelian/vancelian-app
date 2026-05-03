import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import {
  slugify,
  isValidSlug,
  calculateUrlPath,
  calculateExclusiveOfferPageUrlPath,
} from '@/lib/utils/slugify'
import { ContentStatus } from '@prisma/client'
import {
  EXCLUSIVE_OFFER_GABARIT_SLUG,
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
  VAULT_BUILDER_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'
import { defaultLocale } from '@/config/locales'
import { parseCommonModulesDocument } from '@/lib/cms/commonModulesStorage'
import { pageHasAnyHeroSection } from '@/lib/sections/heroSlotPolicy'

function pageUrlPathForTemplate(slug: string, template: string): string {
  if (template === VAULT_BUILDER_TEMPLATE) {
    return calculateExclusiveOfferPageUrlPath(slug)
  }
  if (template === EXCLUSIVE_OFFER_GABARIT_TEMPLATE) {
    return calculateUrlPath(slug)
  }
  return calculateUrlPath(slug)
}

const updatePageSchema = z.object({
  title: z.string().max(200).optional(),
  slug: z.string().min(1).max(60).refine(isValidSlug, {
    message: 'Slug must be lowercase, alphanumeric with hyphens only',
  }),
  description: z.string().max(1000).optional().nullable(),
  template: z.enum(['homepage', 'blog', 'article', 'exclusive_offer']).optional(),
  themeColor: z.enum(['dark', 'light']).optional(),
})

// GET /api/admin/pages/[slug] - Get page details with sections
export async function GET(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const page = await prisma.page.findUnique({
      where: { slug: params.slug },
      include: {
        navMegaIconMedia: {
          select: {
            id: true,
            url: true,
            filename: true,
            alt: true,
            mimeType: true,
          },
        },
        pageI18n: {
          select: {
            locale: true,
            title: true,
            description: true,
            navMegaCategory: true,
            navMegaDescription: true,
          },
        },
        sections: {
          orderBy: { order: 'asc' },
          include: {
            contents: {
              select: { locale: true, status: true },
            },
          },
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const [gs, heroProbeSections] = await Promise.all([
      prisma.globalSettings.findFirst({
        select: { commonModulesJson: true },
      }),
      prisma.section.findMany({
        where: { pageId: page.id },
        select: {
          key: true,
          contents: {
            where: { locale: defaultLocale },
            orderBy: { updatedAt: 'desc' },
            take: 1,
            select: { data: true },
          },
        },
      }),
    ])
    const commonModulesDoc = parseCommonModulesDocument(gs?.commonModulesJson ?? null)
    const hasHeroModule = pageHasAnyHeroSection(heroProbeSections, commonModulesDoc)

    const primaryNavItems = await prisma.menuItem.findMany({
      where: {
        pageId: page.id,
        menu: { key: 'primary' },
      },
      select: {
        id: true,
        type: true,
        isRoot: true,
        navigationNodeKind: true,
        order: true,
        label: true,
      },
      orderBy: { order: 'asc' },
    })

    const navigablePrimary = primaryNavItems.filter(
      (i) => String(i.type) !== 'LANGUAGE_SWITCHER',
    )

    let primaryNavLinkState: {
      status: 'unlinked' | 'content_page' | 'navigation_hub' | 'external_link'
      linkedCount: number
      multipleLinked: boolean
      menuItemIds: string[]
    }

    if (navigablePrimary.length === 0) {
      primaryNavLinkState = {
        status: 'unlinked',
        linkedCount: 0,
        multipleLinked: false,
        menuItemIds: [],
      }
    } else if (
      navigablePrimary.some((i) => i.navigationNodeKind === 'EXTERNAL_LINK')
    ) {
      primaryNavLinkState = {
        status: 'external_link',
        linkedCount: navigablePrimary.length,
        multipleLinked: navigablePrimary.length > 1,
        menuItemIds: navigablePrimary.map((i) => i.id),
      }
    } else {
      const allGroup = navigablePrimary.every(
        (i) => (i.navigationNodeKind ?? 'PAGE') === 'GROUP',
      )
      primaryNavLinkState = {
        status: allGroup ? 'navigation_hub' : 'content_page',
        linkedCount: navigablePrimary.length,
        multipleLinked: navigablePrimary.length > 1,
        menuItemIds: navigablePrimary.map((i) => i.id),
      }
    }

    const [childPageCount, packagedProductRow] = await Promise.all([
      prisma.page.count({ where: { parentId: page.id } }),
      prisma.packagedProduct.findUnique({
        where: { pageId: page.id },
        select: { id: true },
      }),
    ])

    let deleteBlockedReason: string | null = null
    if (page.slug === 'home') {
      deleteBlockedReason =
        'La page d’accueil est réservée et ne peut pas être supprimée.'
    } else if (page.slug === EXCLUSIVE_OFFER_GABARIT_SLUG) {
      deleteBlockedReason =
        'Le gabarit « exclusive-offer » est réservé ; supprimez plutôt le contenu si besoin.'
    } else if (page.isSystemPage) {
      deleteBlockedReason = 'Cette page système ne peut pas être supprimée.'
    } else if (childPageCount > 0) {
      deleteBlockedReason = `Cette page a ${childPageCount} sous-page(s). Déplacez ou supprimez-les d’abord.`
    } else if (packagedProductRow) {
      deleteBlockedReason =
        'Cette page est liée à un produit packagé. Retirez ou dissociez le produit catalogue avant suppression.'
    }

    return NextResponse.json({
      page: {
        ...page,
        hasHeroModule,
        primaryNavLinkState,
        deleteBlockedReason,
      },
    })
  } catch (error) {
    console.error('Error fetching page:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// PUT /api/admin/pages/[slug] - Update page settings
export async function PUT(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = updatePageSchema.parse(body)

    const existingPage = await prisma.page.findUnique({
      where: { slug: params.slug },
    })

    if (!existingPage) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    // Check if slug is being changed
    if (validated.slug && validated.slug !== params.slug) {
      // Prevent changing "home" to something else (home is reserved)
      if (params.slug === 'home' && validated.slug !== 'home') {
        return NextResponse.json(
          { error: 'Cannot rename "home" page. It is reserved for the homepage.' },
          { status: 400 }
        )
      }

      // Check if new slug already exists
      const slugExists = await prisma.page.findUnique({
        where: { slug: validated.slug },
      })

      if (slugExists) {
        return NextResponse.json(
          { error: 'A page with this slug already exists' },
          { status: 409 }
        )
      }

      // Calculate new urlPath (offres exclusive : /projects/[slug])
      const newUrlPath = pageUrlPathForTemplate(validated.slug, existingPage.template)

      // Check if urlPath already exists
      const urlPathExists = await prisma.page.findUnique({
        where: { urlPath: newUrlPath },
      })

      if (urlPathExists) {
        return NextResponse.json(
          { error: 'A page with this URL path already exists' },
          { status: 409 }
        )
      }
    }

    // Update page
    const urlPath = validated.slug
      ? pageUrlPathForTemplate(validated.slug, existingPage.template)
      : existingPage.urlPath
    const updateData: any = {
      title: validated.title !== undefined ? validated.title : undefined,
      description: validated.description !== undefined ? validated.description : undefined,
      template: validated.template !== undefined ? validated.template : undefined,
      themeColor: validated.themeColor !== undefined ? validated.themeColor : undefined,
    }

    if (validated.slug && validated.slug !== params.slug) {
      updateData.slug = validated.slug
      updateData.urlPath = urlPath
    }

    const updatedPage = await prisma.page.update({
      where: { slug: params.slug },
      data: updateData,
    })

    return NextResponse.json({ page: updatedPage })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating page:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// DELETE /api/admin/pages/[slug] - Delete page, sections, contenus, entrées menu liées (pas de fantômes)
export async function DELETE(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const page = await prisma.page.findUnique({
      where: { slug: params.slug },
      select: {
        id: true,
        slug: true,
        isSystemPage: true,
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    if (page.slug === 'home') {
      return NextResponse.json(
        { error: 'La page d’accueil ne peut pas être supprimée.' },
        { status: 400 },
      )
    }

    if (page.slug === EXCLUSIVE_OFFER_GABARIT_SLUG) {
      return NextResponse.json(
        {
          error:
            'Le gabarit « exclusive-offer » est réservé et ne peut pas être supprimé.',
        },
        { status: 400 },
      )
    }

    if (page.isSystemPage) {
      return NextResponse.json(
        { error: 'Cette page système ne peut pas être supprimée.' },
        { status: 400 },
      )
    }

    const [childPageCount, packagedProductRow] = await Promise.all([
      prisma.page.count({ where: { parentId: page.id } }),
      prisma.packagedProduct.findUnique({
        where: { pageId: page.id },
        select: { id: true },
      }),
    ])

    if (childPageCount > 0) {
      return NextResponse.json(
        {
          error: `Impossible de supprimer : ${childPageCount} sous-page(s) encore rattachée(s).`,
          code: 'CHILD_PAGES',
        },
        { status: 409 },
      )
    }

    if (packagedProductRow) {
      return NextResponse.json(
        {
          error:
            'Impossible de supprimer : la page est liée à un produit packagé (RESTRICT).',
          code: 'PACKAGED_PRODUCT',
        },
        { status: 409 },
      )
    }

    await prisma.$transaction(async (tx) => {
      await tx.menuItem.deleteMany({ where: { pageId: page.id } })
      await tx.page.delete({ where: { id: page.id } })
    })

    return NextResponse.json({ ok: true, message: 'Page supprimée.' })
  } catch (error) {
    console.error('Error deleting page:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 },
    )
  }
}

