import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { translateText } from '@/lib/translate/translateText'
import { getGlossary } from '@/lib/translate/getGlossary'
import { supportedLocales, isValidLocale } from '@/config/locales'
import { TranslationEntityType, TranslationLogStatus, TranslationStatus } from '@prisma/client'
import { OPENAI_MODEL } from '@/lib/openai/client'
import { EmailSpec, Block } from '@/components/ai-email/types'

const translateEmailSchema = z.object({
  emailId: z.string().min(1),
  sourceLocale: z.string().refine(isValidLocale, { message: 'Invalid source locale' }),
  targetLocales: z.array(z.string().refine(isValidLocale, { message: 'Invalid target locale' })).min(1).max(10),
  mode: z.enum(['missing', 'force']).default('missing'),
})

/**
 * Translate EmailSpec content-only (never modify structure)
 * Only translates: subject, preheader, and text props of blocks
 */
async function translateEmailSpec(
  sourceSpec: EmailSpec,
  targetLocale: string,
  sourceLocale: string,
  glossary: any
): Promise<EmailSpec> {
  // Translate subject
  const subjectResult = await translateText(sourceSpec.subject || '', {
    sourceLocale,
    targetLocale,
    glossary,
  })
  const translatedSubject = subjectResult.text

  // Translate preheader
  let translatedPreheader: string | undefined
  if (sourceSpec.preheader) {
    const preheaderResult = await translateText(sourceSpec.preheader, {
      sourceLocale,
      targetLocale,
      glossary,
    })
    translatedPreheader = preheaderResult.text
  }

  // Translate blocks (content only, preserve structure)
  const translatedBlocks: Block[] = []
  for (const block of sourceSpec.blocks) {
    const translatedBlock = await translateBlockContent(block, sourceLocale, targetLocale, glossary)
    translatedBlocks.push(translatedBlock)
  }

  return {
    ...sourceSpec,
    subject: translatedSubject,
    preheader: translatedPreheader,
    locale: targetLocale,
    blocks: translatedBlocks,
  }
}

/**
 * Translate block content (text props only)
 * Preserves structure, type, variant, URLs
 */
async function translateBlockContent(
  block: Block,
  sourceLocale: string,
  targetLocale: string,
  glossary: any
): Promise<Block> {
  const blockType = block.type

  if (blockType === 'hero') {
    const heroBlock = block as any
    const translatedTitle = await translateText(heroBlock.title || '', {
      sourceLocale,
      targetLocale,
      glossary,
    }).then((r) => r.text)

    let translatedSubtitle: string | undefined
    if (heroBlock.subtitle) {
      translatedSubtitle = (
        await translateText(heroBlock.subtitle, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    let translatedCtaLabel: string | undefined
    if (heroBlock.cta_label) {
      translatedCtaLabel = (
        await translateText(heroBlock.cta_label, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    return {
      ...heroBlock,
      title: translatedTitle,
      subtitle: translatedSubtitle,
      cta_label: translatedCtaLabel,
      // Keep image_url, cta_url unchanged
    }
  }

  if (blockType === 'section_title') {
    const sectionBlock = block as any
    const translatedTitle = await translateText(sectionBlock.title || '', {
      sourceLocale,
      targetLocale,
      glossary,
    }).then((r) => r.text)

    let translatedSubtitle: string | undefined
    if (sectionBlock.subtitle) {
      translatedSubtitle = (
        await translateText(sectionBlock.subtitle, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    return {
      ...sectionBlock,
      title: translatedTitle,
      subtitle: translatedSubtitle,
    }
  }

  if (blockType === 'text') {
    const textBlock = block as any
    let translatedHeading: string | undefined
    if (textBlock.heading) {
      translatedHeading = (
        await translateText(textBlock.heading, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    const translatedBody = await translateText(textBlock.body || '', {
      sourceLocale,
      targetLocale,
      glossary,
    }).then((r) => r.text)

    return {
      ...textBlock,
      heading: translatedHeading,
      body: translatedBody,
    }
  }

  if (blockType === 'bullets') {
    const bulletsBlock = block as any
    let translatedHeading: string | undefined
    if (bulletsBlock.heading) {
      translatedHeading = (
        await translateText(bulletsBlock.heading, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    const translatedItems = await Promise.all(
      (bulletsBlock.items || []).map((item: string) =>
        translateText(item, {
          sourceLocale,
          targetLocale,
          glossary,
        }).then((r) => r.text)
      )
    )

    return {
      ...bulletsBlock,
      heading: translatedHeading,
      items: translatedItems,
    }
  }

  if (blockType === 'feature_cards') {
    const cardsBlock = block as any
    let translatedHeading: string | undefined
    if (cardsBlock.heading) {
      translatedHeading = (
        await translateText(cardsBlock.heading, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    const translatedItems = await Promise.all(
      (cardsBlock.items || []).map(async (item: any) => {
        const translatedTitle = await translateText(item.title || '', {
          sourceLocale,
          targetLocale,
          glossary,
        }).then((r) => r.text)

        const translatedBody = await translateText(item.body || '', {
          sourceLocale,
          targetLocale,
          glossary,
        }).then((r) => r.text)

        return {
          ...item,
          title: translatedTitle,
          body: translatedBody,
          // Keep icon unchanged
        }
      })
    )

    return {
      ...cardsBlock,
      heading: translatedHeading,
      items: translatedItems,
    }
  }

  if (blockType === 'cta') {
    const ctaBlock = block as any
    const translatedLabel = await translateText(ctaBlock.label || '', {
      sourceLocale,
      targetLocale,
      glossary,
    }).then((r) => r.text)

    let translatedHint: string | undefined
    if (ctaBlock.hint) {
      translatedHint = (
        await translateText(ctaBlock.hint, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    return {
      ...ctaBlock,
      label: translatedLabel,
      hint: translatedHint,
      // Keep url unchanged
    }
  }

  if (blockType === 'image') {
    const imageBlock = block as any
    let translatedAltText: string | undefined
    if (imageBlock.alt_text) {
      translatedAltText = (
        await translateText(imageBlock.alt_text, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    let translatedCaption: string | undefined
    if (imageBlock.caption) {
      translatedCaption = (
        await translateText(imageBlock.caption, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    return {
      ...imageBlock,
      alt_text: translatedAltText,
      caption: translatedCaption,
      // Keep image_url unchanged
    }
  }

  if (blockType === 'footer') {
    const footerBlock = block as any
    const translatedCompanyName = await translateText(footerBlock.company_name || '', {
      sourceLocale,
      targetLocale,
      glossary,
    }).then((r) => r.text)

    let translatedAddress: string | undefined
    if (footerBlock.address) {
      translatedAddress = (
        await translateText(footerBlock.address, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      ).text
    }

    return {
      ...footerBlock,
      company_name: translatedCompanyName,
      address: translatedAddress,
      // Keep unsubscribe_url_placeholder unchanged
    }
  }

  // For divider, spacer: no content to translate
  return block
}

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { emailId, sourceLocale, targetLocales, mode } = translateEmailSchema.parse(body)

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

    // Get email
    const email = await prisma.email.findUnique({
      where: { id: emailId },
    })

    if (!email) {
      return NextResponse.json({ error: 'Email not found' }, { status: 404 })
    }

    // Authorized only if Email.status === VALIDATED
    if (email.status !== 'VALIDATED') {
      return NextResponse.json(
        { error: 'Email must be validated before translation. Please validate the email first.' },
        { status: 400 }
      )
    }

    // Get source spec
    const sourceSpec = email.spec as unknown as EmailSpec

    // Verify source locale matches
    if (sourceSpec.locale !== sourceLocale) {
      return NextResponse.json(
        { error: `Source locale mismatch. Email locale is ${sourceSpec.locale}, but ${sourceLocale} was provided.` },
        { status: 400 }
      )
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
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.EMAIL,
            entityId: emailId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.SKIPPED,
            model: OPENAI_MODEL,
          },
        })
        continue
      }

      try {
        // Check if target already exists
        const existing = await prisma.emailI18n.findUnique({
          where: {
            emailId_locale: {
              emailId,
              locale: targetLocale,
            },
          },
        })

        // In "missing" mode, check if translation is actually needed
        if (mode === 'missing' && existing) {
          results.skipped.push(targetLocale)
          await prisma.translationLog.create({
            data: {
              entityType: TranslationEntityType.EMAIL,
              entityId: emailId,
              sourceLocale,
              targetLocale,
              mode,
              status: TranslationLogStatus.SKIPPED,
              model: OPENAI_MODEL,
            },
          })
          continue
        }

        // Translate EmailSpec (content only)
        const translatedSpec = await translateEmailSpec(
          sourceSpec,
          targetLocale,
          sourceLocale,
          glossary
        )

        // Create or update EmailI18n
        const emailI18n = await prisma.emailI18n.upsert({
          where: {
            emailId_locale: {
              emailId,
              locale: targetLocale,
            },
          },
          create: {
            emailId,
            locale: targetLocale,
            spec: translatedSpec as any,
            translationStatus: TranslationStatus.MACHINE,
          },
          update: {
            spec: translatedSpec as any,
            translationStatus: TranslationStatus.MACHINE,
          },
        })

        // Log success
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.EMAIL,
            entityId: emailId,
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
        console.error(`[Translate][EMAIL][${emailId}] Error for ${targetLocale}:`, error)
        results.errors.push({
          locale: targetLocale,
          error: error.message || 'Translation failed',
        })

        // Log error
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.EMAIL,
            entityId: emailId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.ERROR,
            model: OPENAI_MODEL,
            errorMessage: error.message || 'Translation failed',
          },
        })
      }
    }

    return NextResponse.json({
      success: true,
      results,
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error translating email:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}


