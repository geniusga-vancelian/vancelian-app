import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { translateText } from '@/lib/translate/translateText'
import { translateMarkdown } from '@/lib/translate/translateMarkdown'
import { getGlossary } from '@/lib/translate/getGlossary'
import { supportedLocales, isValidLocale } from '@/config/locales'
import { Prisma, TranslationEntityType, TranslationLogStatus, TranslationStatus } from '@prisma/client'
import { OPENAI_MODEL } from '@/lib/openai/client'

const translateProjectSchema = z.object({
  projectId: z.string().min(1),
  sourceLocale: z.string().refine(isValidLocale, { message: 'Invalid source locale' }),
  targetLocales: z.array(z.string().refine(isValidLocale, { message: 'Invalid target locale' })).min(1).max(10),
  mode: z.enum(['missing', 'force']).default('missing'),
})

// Truncate meta fields to SEO limits
function truncateMeta(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
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

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { projectId, sourceLocale, targetLocales, mode } = translateProjectSchema.parse(body)

    // Validate: sourceLocale must not be in targetLocales
    if (targetLocales.includes(sourceLocale)) {
      return NextResponse.json(
        { error: 'Source locale cannot be in target locales' },
        { status: 400 }
      )
    }

    // Validate: targetLocales must be distinct
    if (new Set(targetLocales).size !== targetLocales.length) {
      return NextResponse.json(
        { error: 'Target locales must be distinct' },
        { status: 400 }
      )
    }

    // Get source i18n
    const sourceI18n = await prisma.projectI18n.findUnique({
      where: {
        projectId_locale: {
          projectId,
          locale: sourceLocale,
        },
      },
    })

    if (!sourceI18n) {
      return NextResponse.json({ error: 'Source project i18n not found' }, { status: 404 })
    }

    // Get glossary
    const glossary = await getGlossary()

    const results = {
      created: [] as string[],
      updated: [] as string[],
      skipped: [] as string[],
      errors: [] as Array<{ locale: string; error: string }>,
    }

    // Translate to each target locale
    for (const targetLocale of targetLocales) {
      if (targetLocale === sourceLocale) {
        results.skipped.push(targetLocale)
        continue
      }

      try {
        // Check if target already exists
        const existing = await prisma.projectI18n.findUnique({
          where: {
            projectId_locale: {
              projectId,
              locale: targetLocale,
            },
          },
        })

        if (existing && mode === 'missing') {
          results.skipped.push(targetLocale)
          // Log skipped
          await prisma.translationLog.create({
            data: {
              entityType: TranslationEntityType.PROJECT,
              entityId: projectId,
              sourceLocale,
              targetLocale,
              mode,
              status: TranslationLogStatus.SKIPPED,
              model: OPENAI_MODEL,
            },
          })
          continue
        }

        const translationOptions = {
          sourceLocale,
          targetLocale,
          glossary: glossary || undefined,
        }

        // Log translation start (dev only)
        if (process.env.NODE_ENV !== 'production') {
          console.log(
            `[Translate][PROJECT][${projectId}] source=${sourceLocale} target=${targetLocale} mode=${mode}`
          )
        }

        // Translate all fields
        const [
          titleResult,
          shortDescResult,
          descResult,
          descriptionLinksResult,
          metaTitleResult,
          metaDescResult,
          competitiveAdvantagesResult,
          howItWorksResult,
          keyInformationResult,
        ] =
          await Promise.all([
            sourceI18n.title
              ? translateText(sourceI18n.title, translationOptions)
              : Promise.resolve({ translated: '' }),
            sourceI18n.shortDescription
              ? translateText(sourceI18n.shortDescription, translationOptions)
              : Promise.resolve({ translated: null }),
            sourceI18n.description
              ? translateMarkdown(sourceI18n.description, translationOptions)
              : Promise.resolve({ translated: null }),
            (async () => {
              const raw = sourceI18n.descriptionLinks as any
              if (!Array.isArray(raw)) return null
              const translated = await Promise.all(
                raw.map(async (link: any) => {
                  const urlRaw = typeof link?.url === 'string' ? normalizeExternalUrl(link.url) : ''
                  if (!urlRaw) return null
                  const baseLabelRaw = deriveLinkLabel(
                    typeof link?.label === 'string' ? link.label : '',
                    urlRaw
                  )
                  const labelTr = baseLabelRaw
                    ? await translateText(baseLabelRaw, translationOptions)
                    : { translated: deriveLinkLabel('', urlRaw) }
                  return {
                    label: labelTr.translated,
                    url: urlRaw,
                  }
                })
              )
              return translated.filter(Boolean)
            })(),
            sourceI18n.metaTitle
              ? translateText(sourceI18n.metaTitle, translationOptions).then((r) => ({
                  translated: truncateMeta(r.translated, 60),
                }))
              : Promise.resolve({ translated: null }),
            sourceI18n.metaDescription
              ? translateText(sourceI18n.metaDescription, translationOptions).then((r) => ({
                  translated: truncateMeta(r.translated, 160),
                }))
              : Promise.resolve({ translated: null }),
            (async () => {
              const raw = sourceI18n.competitiveAdvantages as any
              if (!raw || typeof raw !== 'object') return null
              const titleRaw = typeof raw.title === 'string' ? raw.title.trim() : ''
              const rowsRaw = Array.isArray(raw.rows) ? raw.rows : []

              const translatedTitle = titleRaw
                ? (await translateText(titleRaw, translationOptions)).translated
                : null

              const translatedRows = await Promise.all(
                rowsRaw.map(async (row: any) => {
                  const rowTitle = typeof row?.title === 'string' ? row.title.trim() : ''
                  const rowDescription =
                    typeof row?.description === 'string' ? row.description.trim() : ''
                  if (!rowTitle || !rowDescription) return null
                  const [rowTitleTr, rowDescTr] = await Promise.all([
                    translateText(rowTitle, translationOptions),
                    translateText(rowDescription, translationOptions),
                  ])
                  return {
                    icon:
                      typeof row?.icon === 'string' && row.icon.trim().length > 0
                        ? row.icon.trim()
                        : 'check_circle_rounded',
                    iconBackgroundColor:
                      typeof row?.iconBackgroundColor === 'string' &&
                      row.iconBackgroundColor.trim().length > 0
                        ? row.iconBackgroundColor.trim()
                        : '#1E88E5',
                    title: rowTitleTr.translated,
                    description: rowDescTr.translated,
                  }
                })
              )

              return {
                title: translatedTitle,
                rows: translatedRows.filter(Boolean),
              }
            })(),
            (async () => {
              const raw = sourceI18n.howItWorks as any
              if (!raw || typeof raw !== 'object') return null
              const titleRaw = typeof raw.title === 'string' ? raw.title.trim() : ''
              const contentRaw = typeof raw.content === 'string' ? raw.content.trim() : ''
              const linksRaw = Array.isArray(raw.links) ? raw.links : []

              const translatedTitle = titleRaw
                ? (await translateText(titleRaw, translationOptions)).translated
                : null
              const translatedContent = contentRaw
                ? (await translateMarkdown(contentRaw, translationOptions)).translated
                : null
              const translatedLinks = await Promise.all(
                linksRaw.map(async (link: any) => {
                  const labelRaw = typeof link?.label === 'string' ? link.label.trim() : ''
                  const urlRaw = typeof link?.url === 'string' ? link.url.trim() : ''
                  if (!labelRaw || !urlRaw) return null
                  const labelTr = await translateText(labelRaw, translationOptions)
                  return {
                    label: labelTr.translated,
                    url: urlRaw,
                  }
                })
              )

              return {
                title: translatedTitle,
                content: translatedContent,
                links: translatedLinks.filter(Boolean),
              }
            })(),
            (async () => {
              const raw = sourceI18n.keyInformation as any
              if (!raw || typeof raw !== 'object') return null
              const titleRaw = typeof raw.title === 'string' ? raw.title.trim() : ''
              const rowsRaw = Array.isArray(raw.rows) ? raw.rows : []

              const translatedTitle = titleRaw
                ? (await translateText(titleRaw, translationOptions)).translated
                : null

              const translatedRows = await Promise.all(
                rowsRaw.map(async (row: any) => {
                  const labelRaw = typeof row?.label === 'string' ? row.label.trim() : ''
                  const valueRaw = typeof row?.value === 'string' ? row.value.trim() : ''
                  if (!labelRaw || !valueRaw) return null
                  const [labelTr, valueTr] = await Promise.all([
                    translateText(labelRaw, translationOptions),
                    translateText(valueRaw, translationOptions),
                  ])
                  let infoTitle: string | null = null
                  let infoContent: string | null = null
                  if (typeof row?.infoTitle === 'string' && row.infoTitle.trim().length > 0) {
                    infoTitle = (await translateText(row.infoTitle.trim(), translationOptions)).translated
                  }
                  if (typeof row?.infoContent === 'string' && row.infoContent.trim().length > 0) {
                    infoContent = (await translateMarkdown(row.infoContent.trim(), translationOptions)).translated
                  }
                  return {
                    categoryKey:
                      typeof row?.categoryKey === 'string' && row.categoryKey.trim().length > 0
                        ? row.categoryKey.trim()
                        : 'custom',
                    label: labelTr.translated,
                    value: valueTr.translated,
                    showInfoIcon: row?.showInfoIcon === true,
                    infoTitle,
                    infoContent,
                  }
                })
              )

              return {
                title: translatedTitle,
                rows: translatedRows.filter(Boolean),
              }
            })(),
          ])

        // Upsert target i18n with MACHINE status
        // CRITICAL: Ensure locale is correctly set in where clause to prevent mixing
        const upsertResult = await prisma.projectI18n.upsert({
          where: {
            projectId_locale: {
              projectId,
              locale: targetLocale, // ✅ Explicitly set target locale
            },
          },
          create: {
            projectId,
            locale: targetLocale, // ✅ Explicitly set target locale
            title: titleResult.translated,
            shortDescription: shortDescResult.translated,
            description: descResult.translated,
            descriptionLinks: toNullableJsonInput(descriptionLinksResult),
            metaTitle: metaTitleResult.translated,
            metaDescription: metaDescResult.translated,
            competitiveAdvantages: toNullableJsonInput(competitiveAdvantagesResult),
            howItWorks: toNullableJsonInput(howItWorksResult),
            keyInformation: toNullableJsonInput(keyInformationResult),
            location: sourceI18n.location, // Keep location as-is (usually proper nouns)
            translationStatus: TranslationStatus.MACHINE,
          },
          update: {
            title: titleResult.translated,
            shortDescription: shortDescResult.translated,
            description: descResult.translated,
            descriptionLinks: toNullableJsonInput(descriptionLinksResult),
            metaTitle: metaTitleResult.translated,
            metaDescription: metaDescResult.translated,
            competitiveAdvantages: toNullableJsonInput(competitiveAdvantagesResult),
            howItWorks: toNullableJsonInput(howItWorksResult),
            keyInformation: toNullableJsonInput(keyInformationResult),
            translationStatus: TranslationStatus.MACHINE, // Mark as machine-translated
          },
        })

        // Verify the write (dev only)
        if (process.env.NODE_ENV !== 'production') {
          const verify = await prisma.projectI18n.findUnique({
            where: {
              projectId_locale: {
                projectId,
                locale: targetLocale,
              },
            },
          })
          if (verify && verify.locale !== targetLocale) {
            console.error(
              `[Translate][PROJECT] ERROR: Written locale mismatch! Expected ${targetLocale}, got ${verify.locale}`
            )
          }
        }

        // Log success
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.PROJECT,
            entityId: projectId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.SUCCESS,
            model: OPENAI_MODEL,
          },
        })

        if (existing) {
          results.updated.push(targetLocale)
        } else {
          results.created.push(targetLocale)
        }
      } catch (error: any) {
        console.error(`Error translating project to ${targetLocale}:`, error)
        const errorMessage = error.message || 'Translation failed'
        results.errors.push({
          locale: targetLocale,
          error: errorMessage,
        })

        // Log error (sanitize message)
        const sanitizedError = errorMessage.length > 500 ? errorMessage.substring(0, 500) : errorMessage
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.PROJECT,
            entityId: projectId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.ERROR,
            model: OPENAI_MODEL,
            errorMessage: sanitizedError,
          },
        })
      }
    }

    return NextResponse.json({ results })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error in translate project:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

