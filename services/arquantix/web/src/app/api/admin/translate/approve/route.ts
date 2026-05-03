import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { TranslationEntityType, TranslationStatus } from '@prisma/client'
import { isValidLocale } from '@/config/locales'

const approveTranslationSchema = z.object({
  entityType: z.enum([
    'SECTION',
    'PROJECT',
    'ARTICLE',
    'MENU_ITEM',
    'ARTICLE_CATEGORY',
    'MENU',
    'HELP_COLLECTION',
    'HELP_CATEGORY',
    'HELP_ARTICLE',
    'ACADEMY_COLLECTION',
    'ACADEMY_CATEGORY',
    'EMAIL',
    'EMAIL_MODULE',
  ]),
  entityId: z.string().min(1),
  locale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { entityType, entityId, locale } = approveTranslationSchema.parse(body)

    if (entityType === 'SECTION') {
      // Find all SectionContent for this section and locale (both DRAFT and PUBLISHED)
      const contents = await prisma.sectionContent.findMany({
        where: {
          sectionId: entityId,
          locale,
        },
      })

      if (contents.length === 0) {
        return NextResponse.json(
          { error: 'Section content not found for this locale' },
          { status: 404 }
        )
      }

      // Update all statuses to APPROVED
      await prisma.sectionContent.updateMany({
        where: {
          sectionId: entityId,
          locale,
          translationStatus: TranslationStatus.MACHINE,
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'PROJECT') {
      const i18n = await prisma.projectI18n.findUnique({
        where: {
          projectId_locale: {
            projectId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Project i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.projectI18n.update({
        where: {
          projectId_locale: {
            projectId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'ARTICLE') {
      const i18n = await prisma.articleI18n.findUnique({
        where: {
          articleId_locale: {
            articleId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Article i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.articleI18n.update({
        where: {
          articleId_locale: {
            articleId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'MENU_ITEM') {
      const i18n = await prisma.menuItemI18n.findUnique({
        where: {
          menuItemId_locale: {
            menuItemId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Menu item i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.menuItemI18n.update({
        where: {
          menuItemId_locale: {
            menuItemId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'ARTICLE_CATEGORY') {
      const i18n = await prisma.articleCategoryI18n.findUnique({
        where: {
          categoryId_locale: {
            categoryId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Category i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.articleCategoryI18n.update({
        where: {
          categoryId_locale: {
            categoryId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'MENU') {
      const i18n = await prisma.menuI18n.findUnique({
        where: {
          menuId_locale: {
            menuId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Menu i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.menuI18n.update({
        where: {
          menuId_locale: {
            menuId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'HELP_COLLECTION') {
      const i18n = await prisma.helpCollectionI18n.findUnique({
        where: {
          collectionId_locale: {
            collectionId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Collection i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.helpCollectionI18n.update({
        where: {
          collectionId_locale: {
            collectionId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'HELP_CATEGORY') {
      const i18n = await prisma.helpCategoryI18n.findUnique({
        where: {
          categoryId_locale: {
            categoryId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Category i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.helpCategoryI18n.update({
        where: {
          categoryId_locale: {
            categoryId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'ACADEMY_COLLECTION') {
      const i18n = await prisma.academyCollectionI18n.findUnique({
        where: {
          collectionId_locale: {
            collectionId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Academy collection i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.academyCollectionI18n.update({
        where: {
          collectionId_locale: {
            collectionId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'ACADEMY_CATEGORY') {
      const i18n = await prisma.academyCategoryI18n.findUnique({
        where: {
          categoryId_locale: {
            categoryId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Academy category i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.academyCategoryI18n.update({
        where: {
          categoryId_locale: {
            categoryId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'HELP_ARTICLE') {
      const i18n = await prisma.helpArticleI18n.findUnique({
        where: {
          articleId_locale: {
            articleId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Article i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.helpArticleI18n.update({
        where: {
          articleId_locale: {
            articleId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'EMAIL') {
      const i18n = await prisma.emailI18n.findUnique({
        where: {
          emailId_locale: {
            emailId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Email i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.emailI18n.update({
        where: {
          emailId_locale: {
            emailId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else if (entityType === 'EMAIL_MODULE') {
      const i18n = await prisma.emailModuleI18n.findUnique({
        where: {
          moduleId_locale: {
            moduleId: entityId,
            locale,
          },
        },
      })

      if (!i18n) {
        return NextResponse.json(
          { error: 'Module i18n not found for this locale' },
          { status: 404 }
        )
      }

      if (i18n.translationStatus !== TranslationStatus.MACHINE) {
        return NextResponse.json(
          { error: 'Translation is not in MACHINE status' },
          { status: 400 }
        )
      }

      await prisma.emailModuleI18n.update({
        where: {
          moduleId_locale: {
            moduleId: entityId,
            locale,
          },
        },
        data: {
          translationStatus: TranslationStatus.APPROVED,
        },
      })

      return NextResponse.json({ message: 'Translation approved' })
    } else {
      return NextResponse.json(
        { error: 'Invalid entity type' },
        { status: 400 }
      )
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error approving translation:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

