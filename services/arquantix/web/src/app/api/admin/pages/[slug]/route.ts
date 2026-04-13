import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { slugify, isValidSlug, calculateUrlPath } from '@/lib/utils/slugify'
import { ContentStatus } from '@prisma/client'

const updatePageSchema = z.object({
  title: z.string().max(200).optional(),
  slug: z.string().min(1).max(60).refine(isValidSlug, {
    message: 'Slug must be lowercase, alphanumeric with hyphens only',
  }),
  description: z.string().max(1000).optional().nullable(),
  template: z.enum(['homepage', 'blog']).optional(),
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

    return NextResponse.json({ page })
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

      // Calculate new urlPath
      const newUrlPath = calculateUrlPath(validated.slug)

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
    const urlPath = validated.slug ? calculateUrlPath(validated.slug) : existingPage.urlPath
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

// DELETE /api/admin/pages/[slug] - Delete a page
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
      include: {
        menuItems: true,
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    // Prevent deletion of "home" page
    if (page.slug === 'home') {
      return NextResponse.json(
        { error: 'Cannot delete the "home" page. It is reserved for the homepage.' },
        { status: 400 }
      )
    }

    // Check if page is referenced by menu items
    if (page.menuItems.length > 0) {
      // Disable menu items that reference this page instead of deleting them
      // This prevents breaking the menu structure
      await prisma.menuItem.updateMany({
        where: { pageId: page.id },
        data: { enabled: false },
      })
    }

    // Delete the page (sections and contents will be cascade deleted)
    await prisma.page.delete({
      where: { slug: params.slug },
    })

    return NextResponse.json({ message: 'Page deleted successfully' })
  } catch (error) {
    console.error('Error deleting page:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

