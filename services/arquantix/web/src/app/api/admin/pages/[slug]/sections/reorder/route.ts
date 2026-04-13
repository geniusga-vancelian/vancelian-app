import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const reorderSectionsSchema = z.object({
  orderedSectionIds: z.array(z.string()).min(1, 'At least one section ID is required'),
})

/**
 * POST /api/admin/pages/[slug]/sections/reorder
 * Reorder sections by providing an array of section IDs in the desired order
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
    const validated = reorderSectionsSchema.parse(body)

    // Get page
    const page = await prisma.page.findUnique({
      where: { slug: params.slug },
      include: {
        sections: true,
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    // Verify all section IDs belong to this page
    const pageSectionIds = new Set(page.sections.map((s) => s.id))
    const invalidIds = validated.orderedSectionIds.filter((id) => !pageSectionIds.has(id))
    if (invalidIds.length > 0) {
      return NextResponse.json(
        { error: `Invalid section IDs: ${invalidIds.join(', ')}` },
        { status: 400 }
      )
    }

    // Verify all sections are included
    if (validated.orderedSectionIds.length !== page.sections.length) {
      return NextResponse.json(
        { error: 'All sections must be included in the reorder' },
        { status: 400 }
      )
    }

    // Update order for each section
    const updates = validated.orderedSectionIds.map((sectionId, index) =>
      prisma.section.update({
        where: { id: sectionId },
        data: { order: index },
      })
    )

    await prisma.$transaction(updates)

    return NextResponse.json({ success: true })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error reordering sections:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









