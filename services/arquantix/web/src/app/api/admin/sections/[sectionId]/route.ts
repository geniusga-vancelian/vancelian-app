import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidLocale, supportedLocales } from '@/config/locales'

const updateContentSchema = z.object({
  locale: z.string().refine(isValidLocale, {
    message: 'Invalid locale',
  }),
  data: z.any(), // JSON data, validated per section type
})

// GET /api/admin/sections/[sectionId]?locale=xx&status=draft|published
export async function GET(
  request: NextRequest,
  { params }: { params: { sectionId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const locale = searchParams.get('locale')
    const status = searchParams.get('status')?.toUpperCase()

    if (!locale || !isValidLocale(locale)) {
      return NextResponse.json(
        { error: 'Valid locale is required' },
        { status: 400 }
      )
    }

    if (status !== 'DRAFT' && status !== 'PUBLISHED') {
      return NextResponse.json(
        { error: 'Status must be draft or published' },
        { status: 400 }
      )
    }

    const section = await prisma.section.findUnique({
      where: { id: params.sectionId },
      include: {
        page: true,
        contents: {
          where: {
            locale,
            status: status as 'DRAFT' | 'PUBLISHED',
          },
        },
      },
    })

    if (!section) {
      return NextResponse.json({ error: 'Section not found' }, { status: 404 })
    }

    const content = section.contents[0] || null

    return NextResponse.json({
      section: {
        id: section.id,
        key: section.key,
        order: section.order,
        schemaVersion: section.schemaVersion,
        page: {
          slug: section.page.slug,
        },
      },
      content,
    })
  } catch (error) {
    console.error('Error fetching section:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// PUT /api/admin/sections/[sectionId] - Save draft for locale
export async function PUT(
  request: NextRequest,
  { params }: { params: { sectionId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = updateContentSchema.parse(body)

    const section = await prisma.section.findUnique({
      where: { id: params.sectionId },
    })

    if (!section) {
      return NextResponse.json({ error: 'Section not found' }, { status: 404 })
    }

    // Upsert draft content
    const content = await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: params.sectionId,
          locale: validated.locale,
          status: 'DRAFT',
        },
      },
      update: {
        data: validated.data,
        updatedByUserId: session.userId,
        // Preserve translationStatus if it was MACHINE (user editing doesn't auto-approve)
        // Only explicit approval changes it to APPROVED
      },
      create: {
        sectionId: params.sectionId,
        locale: validated.locale,
        status: 'DRAFT',
        data: validated.data,
        updatedByUserId: session.userId,
      },
    })

    // If this is a FAQ section, synchronize items structure across all locales
    if (section.key === 'faq' && validated.data.items && Array.isArray(validated.data.items)) {
      const sourceItems = validated.data.items as Array<{ id: string; question: string; answerMarkdown: string }>
      const sourceItemIds = new Set(sourceItems.map((item) => item.id))

      // Get all other locales
      const otherLocales = supportedLocales.filter((loc) => loc !== validated.locale)

      for (const targetLocale of otherLocales) {
        try {
          // Get or create draft content for target locale
          const targetContent = await prisma.sectionContent.findUnique({
            where: {
              sectionId_locale_status: {
                sectionId: params.sectionId,
                locale: targetLocale,
                status: 'DRAFT',
              },
            },
          })

          const targetData = targetContent
            ? (targetContent.data as any)
            : {
                title: section.key === 'faq' ? 'FAQ' : '',
                subtitle: section.key === 'faq' ? 'Frequently Asked Questions' : '',
                items: [],
              }

          // Ensure items array exists
          if (!targetData.items || !Array.isArray(targetData.items)) {
            targetData.items = []
          }

          const targetItems = targetData.items as Array<{ id: string; question: string; answerMarkdown: string }>
          const targetItemMap = new Map(targetItems.map((item) => [item.id, item]))

          // Synchronize items: add new ones, remove deleted ones, preserve existing translations
          const syncedItems: Array<{ id: string; question: string; answerMarkdown: string }> = []

          // Add items in the same order as source, preserving existing translations
          for (const sourceItem of sourceItems) {
            const existingItem = targetItemMap.get(sourceItem.id)
            if (existingItem) {
              // Item exists: preserve existing translation (question/answerMarkdown)
              syncedItems.push({
                id: sourceItem.id,
                question: existingItem.question || '',
                answerMarkdown: existingItem.answerMarkdown || '',
              })
            } else {
              // New item: add with empty fields (will be translated later)
              syncedItems.push({
                id: sourceItem.id,
                question: '',
                answerMarkdown: '',
              })
            }
          }

          // Update target locale with synchronized items
          const syncedData = {
            ...targetData,
            title: targetData.title || validated.data.title || 'FAQ',
            subtitle: targetData.subtitle || validated.data.subtitle || 'Frequently Asked Questions',
            items: syncedItems,
          }

          await prisma.sectionContent.upsert({
            where: {
              sectionId_locale_status: {
                sectionId: params.sectionId,
                locale: targetLocale,
                status: 'DRAFT',
              },
            },
            update: {
              data: syncedData,
              updatedByUserId: session.userId,
            },
            create: {
              sectionId: params.sectionId,
              locale: targetLocale,
              status: 'DRAFT',
              data: syncedData,
              updatedByUserId: session.userId,
            },
          })
        } catch (error) {
          console.error(`Error synchronizing FAQ items to locale ${targetLocale}:`, error)
          // Continue with other locales even if one fails
        }
      }
    }

    return NextResponse.json({ content })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error saving draft:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

