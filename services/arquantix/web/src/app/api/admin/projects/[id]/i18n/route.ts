import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidLocale } from '@/config/locales'
import { Prisma } from '@prisma/client'

const updateI18nSchema = z.object({
  locale: z.string().refine(isValidLocale, {
    message: 'Invalid locale',
  }),
  title: z.string().min(1, 'Title is required'),
  location: z.string().optional().nullable(),
  shortDescription: z.string().optional().nullable(),
  description: z.string().optional().nullable(),
  descriptionLinks: z
    .array(
      z.object({
        label: z.string().max(300),
        url: z.string().max(2000),
      })
    )
    .default([]),
  metaTitle: z.string().optional().nullable(),
  metaDescription: z.string().optional().nullable(),
  competitiveAdvantages: z
    .object({
      title: z.string().optional().nullable(),
      rows: z
        .array(
          z.object({
            icon: z.string().min(1).max(100),
            iconBackgroundColor: z.string().min(1).max(20),
            title: z.string().max(300),
            description: z.string().max(4000),
          })
        )
        .default([]),
    })
    .optional()
    .nullable(),
  howItWorks: z
    .object({
      title: z.string().optional().nullable(),
      content: z.string().optional().nullable(),
      links: z
        .array(
          z.object({
            label: z.string().max(300),
            url: z.string().max(2000),
          })
        )
        .default([]),
    })
    .optional()
    .nullable(),
  keyInformation: z
    .object({
      title: z.string().optional().nullable(),
      rows: z
        .array(
          z.object({
            categoryKey: z.string().max(200),
            label: z.string().max(300),
            value: z.string().max(2000),
            showInfoIcon: z.boolean().optional().default(false),
            infoTitle: z.string().optional().nullable(),
            infoContent: z.string().optional().nullable(),
          })
        )
        .default([]),
    })
    .optional()
    .nullable(),
  faq: z
    .object({
      enableTagRedirect: z.boolean().optional().default(false),
      tagRedirectLabel: z.string().max(300).optional().nullable(),
      items: z
        .array(
          z.object({
            articleId: z.string().min(1).max(200),
            articleSlug: z.string().min(1).max(300),
            collectionSlug: z.string().min(1).max(300),
            categorySlug: z.string().min(1).max(300),
            question: z.string().min(1).max(500),
            standfirst: z.string().optional().nullable(),
          })
        )
        .default([]),
    })
    .optional()
    .nullable(),
})

async function ensureProjectI18nCompetitiveAdvantagesColumn() {
  await prisma.$executeRawUnsafe(`
    ALTER TABLE "project_i18n"
    ADD COLUMN IF NOT EXISTS "competitive_advantages" JSONB;
  `)
}

async function ensureProjectI18nHowItWorksColumn() {
  await prisma.$executeRawUnsafe(`
    ALTER TABLE "project_i18n"
    ADD COLUMN IF NOT EXISTS "how_it_works" JSONB;
  `)
}

async function ensureProjectI18nKeyInformationColumn() {
  await prisma.$executeRawUnsafe(`
    ALTER TABLE "project_i18n"
    ADD COLUMN IF NOT EXISTS "key_information" JSONB;
  `)
}

async function ensureProjectI18nDescriptionLinksColumn() {
  await prisma.$executeRawUnsafe(`
    ALTER TABLE "project_i18n"
    ADD COLUMN IF NOT EXISTS "description_links" JSONB;
  `)
}

async function ensureProjectI18nFaqColumn() {
  await prisma.$executeRawUnsafe(`
    ALTER TABLE "project_i18n"
    ADD COLUMN IF NOT EXISTS "faq" JSONB;
  `)
}

function isUnknownCompetitiveAdvantagesArgumentError(error: unknown): boolean {
  return error instanceof Error && error.message.includes('Unknown argument `competitiveAdvantages`')
}

function isUnknownHowItWorksArgumentError(error: unknown): boolean {
  return error instanceof Error && error.message.includes('Unknown argument `howItWorks`')
}

function isUnknownKeyInformationArgumentError(error: unknown): boolean {
  return error instanceof Error && error.message.includes('Unknown argument `keyInformation`')
}

function isUnknownDescriptionLinksArgumentError(error: unknown): boolean {
  return error instanceof Error && error.message.includes('Unknown argument `descriptionLinks`')
}

function isUnknownFaqArgumentError(error: unknown): boolean {
  return error instanceof Error && error.message.includes('Unknown argument `faq`')
}

function toNullableJsonInput(
  value: unknown
): Prisma.InputJsonValue | Prisma.NullableJsonNullValueInput {
  if (value === null) return Prisma.JsonNull
  return value as Prisma.InputJsonValue
}

function normalizeExternalUrl(value: string): string {
  const raw = value.trim()
  if (!raw) return ''
  if (/^https?:\/\//i.test(raw)) return raw
  return `https://${raw}`
}

function deriveLinkLabel(label: string, url: string): string {
  const cleanLabel = label.trim()
  if (cleanLabel.length > 0) return cleanLabel
  const normalizedUrl = normalizeExternalUrl(url)
  if (!normalizedUrl) return ''
  try {
    const parsed = new URL(normalizedUrl)
    return parsed.hostname.replace(/^www\./, '')
  } catch {
    return normalizedUrl
  }
}

// PUT /api/admin/projects/[id]/i18n
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    console.log('Received body:', JSON.stringify(body, null, 2))
    
    const {
      locale,
      title,
      location,
      shortDescription,
      description,
      descriptionLinks,
      metaTitle,
      metaDescription,
      competitiveAdvantages,
      howItWorks,
      keyInformation,
      faq,
    } = updateI18nSchema.parse(body)
    const normalizedCompetitiveAdvantages =
      competitiveAdvantages === undefined
        ? undefined
        : competitiveAdvantages === null
          ? null
          : {
              title:
                competitiveAdvantages.title &&
                competitiveAdvantages.title.trim() !== ''
                  ? competitiveAdvantages.title.trim()
                  : null,
              rows: competitiveAdvantages.rows
                .map((row) => ({
                  icon: row.icon.trim(),
                  iconBackgroundColor: row.iconBackgroundColor.trim(),
                  title: row.title.trim(),
                  description: row.description.trim(),
                })),
            }

    const normalizedKeyInformation =
      keyInformation === undefined
        ? undefined
        : keyInformation === null
          ? null
          : {
              title:
                keyInformation.title && keyInformation.title.trim() !== ''
                  ? keyInformation.title.trim()
                  : null,
              rows: keyInformation.rows
                .map((row) => ({
                  categoryKey: row.categoryKey.trim(),
                  label: row.label.trim(),
                  value: row.value.trim(),
                  showInfoIcon: row.showInfoIcon === true,
                  infoTitle:
                    row.infoTitle && row.infoTitle.trim() !== ''
                      ? row.infoTitle.trim()
                      : null,
                  infoContent:
                    row.infoContent && row.infoContent.trim() !== ''
                      ? row.infoContent.trim()
                      : null,
                }))
                .filter((row) => row.categoryKey.length > 0 && row.label.length > 0 && row.value.length > 0),
            }

    const normalizedDescriptionLinks = descriptionLinks
      .map((link) => ({
        url: normalizeExternalUrl(link.url),
        label: deriveLinkLabel(link.label, link.url),
      }))
      .filter((link) => link.url.length > 0)

    const normalizedHowItWorks =
      howItWorks === undefined
        ? undefined
        : howItWorks === null
          ? null
          : {
              title: howItWorks.title && howItWorks.title.trim() !== '' ? howItWorks.title.trim() : null,
              content:
                howItWorks.content && howItWorks.content.trim() !== ''
                  ? howItWorks.content.trim()
                  : null,
              links: howItWorks.links
                .map((link) => ({
                  label: link.label.trim(),
                  url: link.url.trim(),
                }))
                .filter((link) => link.label.length > 0 && link.url.length > 0),
            }

    const normalizedFaq =
      faq === undefined
        ? undefined
        : faq === null
          ? null
          : {
              enableTagRedirect: faq.enableTagRedirect === true,
              tagRedirectLabel:
                faq.tagRedirectLabel && faq.tagRedirectLabel.trim() !== ''
                  ? faq.tagRedirectLabel.trim()
                  : null,
              items: faq.items
                .map((item) => ({
                  articleId: item.articleId.trim(),
                  articleSlug: item.articleSlug.trim(),
                  collectionSlug: item.collectionSlug.trim(),
                  categorySlug: item.categorySlug.trim(),
                  question: item.question.trim(),
                  standfirst:
                    item.standfirst && item.standfirst.trim() !== ''
                      ? item.standfirst.trim()
                      : null,
                }))
                .filter(
                  (item) =>
                    item.articleId.length > 0 &&
                    item.articleSlug.length > 0 &&
                    item.collectionSlug.length > 0 &&
                    item.categorySlug.length > 0 &&
                    item.question.length > 0
                ),
            }


    // Verify project exists
    const project = await prisma.project.findUnique({
      where: { id: params.id },
    })

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Normalize empty strings to null (handle both undefined and empty strings)
    const normalizedLocation = (location && typeof location === 'string' && location.trim() !== '') ? location.trim() : null
    const normalizedShortDescription = (shortDescription && typeof shortDescription === 'string' && shortDescription.trim() !== '') ? shortDescription.trim() : null
    const normalizedDescription = (description && typeof description === 'string' && description.trim() !== '') ? description.trim() : null
    const normalizedMetaTitle = (metaTitle && typeof metaTitle === 'string' && metaTitle.trim() !== '') ? metaTitle.trim() : null
    const normalizedMetaDescription = (metaDescription && typeof metaDescription === 'string' && metaDescription.trim() !== '') ? metaDescription.trim() : null

    console.log('Normalized values:', {
      location: normalizedLocation,
      shortDescription: normalizedShortDescription,
      description: normalizedDescription,
      descriptionLinks:
        normalizedDescriptionLinks.length > 0
          ? toNullableJsonInput(normalizedDescriptionLinks)
          : Prisma.JsonNull,
      metaTitle: normalizedMetaTitle,
      metaDescription: normalizedMetaDescription,
    })

    // Prepare update data - explicitly include all fields
    const updateData: Prisma.ProjectI18nUpdateInput = {
      title,
      location: normalizedLocation,
      shortDescription: normalizedShortDescription,
      description: normalizedDescription,
      metaTitle: normalizedMetaTitle,
      metaDescription: normalizedMetaDescription,
      ...(normalizedCompetitiveAdvantages !== undefined
        ? { competitiveAdvantages: toNullableJsonInput(normalizedCompetitiveAdvantages) }
        : {}),
      ...(normalizedHowItWorks !== undefined
        ? { howItWorks: toNullableJsonInput(normalizedHowItWorks) }
        : {}),
      ...(normalizedKeyInformation !== undefined
        ? { keyInformation: toNullableJsonInput(normalizedKeyInformation) }
        : {}),
      ...(normalizedFaq !== undefined
        ? { faq: toNullableJsonInput(normalizedFaq) }
        : {}),
    }

    console.log('Update data:', JSON.stringify(updateData, null, 2))
    console.log('Project ID:', params.id)
    console.log('Locale:', locale)

    // Upsert i18n
    const baseCreateData = {
      projectId: params.id,
      locale,
      title,
      location: normalizedLocation,
      shortDescription: normalizedShortDescription,
      description: normalizedDescription,
      metaTitle: normalizedMetaTitle,
      metaDescription: normalizedMetaDescription,
    }
    const updateDataWithoutCompetitiveAdvantages = {
      title,
      location: normalizedLocation,
      shortDescription: normalizedShortDescription,
      description: normalizedDescription,
      metaTitle: normalizedMetaTitle,
      metaDescription: normalizedMetaDescription,
    }

    let i18n
    try {
      i18n = await prisma.projectI18n.upsert({
        where: {
          projectId_locale: {
            projectId: params.id,
            locale,
          },
        },
        update: updateData,
        create: {
          ...baseCreateData,
          competitiveAdvantages: toNullableJsonInput(normalizedCompetitiveAdvantages ?? null),
          howItWorks: toNullableJsonInput(normalizedHowItWorks ?? null),
          keyInformation: toNullableJsonInput(normalizedKeyInformation ?? null),
          faq: toNullableJsonInput(normalizedFaq ?? null),
          descriptionLinks:
            normalizedDescriptionLinks.length > 0
              ? toNullableJsonInput(normalizedDescriptionLinks)
              : Prisma.JsonNull,
        },
      })
      await prisma.$executeRawUnsafe(
        `UPDATE "project_i18n" SET "description_links" = $1::jsonb WHERE "project_id" = $2 AND "locale" = $3`,
        JSON.stringify(normalizedDescriptionLinks),
        params.id,
        locale
      )
    } catch (error) {
      const isMissingCompetitiveAdvantagesColumn =
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === 'P2022' &&
        typeof error.meta?.column === 'string' &&
        error.meta.column.includes('competitive_advantages')

      const isMissingHowItWorksColumn =
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === 'P2022' &&
        typeof error.meta?.column === 'string' &&
        error.meta.column.includes('how_it_works')

      const isMissingKeyInformationColumn =
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === 'P2022' &&
        typeof error.meta?.column === 'string' &&
        error.meta.column.includes('key_information')

      const isMissingDescriptionLinksColumn =
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === 'P2022' &&
        typeof error.meta?.column === 'string' &&
        error.meta.column.includes('description_links')
      const isMissingFaqColumn =
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === 'P2022' &&
        typeof error.meta?.column === 'string' &&
        error.meta.column.includes('faq')

      if (
        !isUnknownCompetitiveAdvantagesArgumentError(error) &&
        !isMissingCompetitiveAdvantagesColumn &&
        !isUnknownHowItWorksArgumentError(error) &&
        !isMissingHowItWorksColumn &&
        !isUnknownKeyInformationArgumentError(error) &&
        !isMissingKeyInformationColumn &&
        !isUnknownDescriptionLinksArgumentError(error) &&
        !isMissingDescriptionLinksColumn &&
        !isUnknownFaqArgumentError(error) &&
        !isMissingFaqColumn
      ) {
        throw error
      }

      await ensureProjectI18nCompetitiveAdvantagesColumn()
      await ensureProjectI18nHowItWorksColumn()
      await ensureProjectI18nKeyInformationColumn()
      await ensureProjectI18nDescriptionLinksColumn()
      await ensureProjectI18nFaqColumn()
      i18n = await prisma.projectI18n.upsert({
        where: {
          projectId_locale: {
            projectId: params.id,
            locale,
          },
        },
        update: updateDataWithoutCompetitiveAdvantages,
        create: baseCreateData,
      })

      if (normalizedCompetitiveAdvantages !== undefined) {
        await prisma.$executeRawUnsafe(
          `UPDATE "project_i18n" SET "competitive_advantages" = $1::jsonb WHERE "project_id" = $2 AND "locale" = $3`,
          JSON.stringify(normalizedCompetitiveAdvantages),
          params.id,
          locale
        )
      }
      if (normalizedHowItWorks !== undefined) {
        await prisma.$executeRawUnsafe(
          `UPDATE "project_i18n" SET "how_it_works" = $1::jsonb WHERE "project_id" = $2 AND "locale" = $3`,
          JSON.stringify(normalizedHowItWorks),
          params.id,
          locale
        )
      }
      if (normalizedKeyInformation !== undefined) {
        await prisma.$executeRawUnsafe(
          `UPDATE "project_i18n" SET "key_information" = $1::jsonb WHERE "project_id" = $2 AND "locale" = $3`,
          JSON.stringify(normalizedKeyInformation),
          params.id,
          locale
        )
      }
      if (normalizedFaq !== undefined) {
        await prisma.$executeRawUnsafe(
          `UPDATE "project_i18n" SET "faq" = $1::jsonb WHERE "project_id" = $2 AND "locale" = $3`,
          JSON.stringify(normalizedFaq),
          params.id,
          locale
        )
      }
      await prisma.$executeRawUnsafe(
        `UPDATE "project_i18n" SET "description_links" = $1::jsonb WHERE "project_id" = $2 AND "locale" = $3`,
        JSON.stringify(normalizedDescriptionLinks),
        params.id,
        locale
      )
    }

    console.log('Upsert successful, i18n:', JSON.stringify(i18n, null, 2))

    return NextResponse.json({ i18n })
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('Zod validation error:', error.issues)
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating project i18n:', error)
    console.error('Error details:', {
      message: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined,
      name: error instanceof Error ? error.name : undefined,
    })
    return NextResponse.json(
      { 
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}

