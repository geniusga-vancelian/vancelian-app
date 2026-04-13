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
import { requestWithRetry } from '@/lib/openai/requestWithRetry'

const translateModuleSchema = z.object({
  moduleId: z.string().uuid(),
  sourceLocale: z.string().refine(isValidLocale, { message: 'Invalid source locale' }),
  targetLocales: z.array(z.string().refine(isValidLocale, { message: 'Invalid target locale' })).min(1).max(10),
  mode: z.enum(['missing', 'force']).default('missing'),
})

/**
 * Translate EmailModule spec content-only (never modify structure)
 * Only translates: text props of blocks
 * Rules: Only if EmailModule.status === VALIDATED
 */
async function translateModuleSpec(
  sourceSpec: EmailSpec,
  targetLocale: string,
  sourceLocale: string,
  glossary: any
): Promise<EmailSpec> {
  // Translate blocks (content only, preserve structure)
  const translatedBlocks: Block[] = []
  for (const block of sourceSpec.blocks) {
    const translatedBlock = await translateBlockContent(block, sourceLocale, targetLocale, glossary)
    translatedBlocks.push(translatedBlock)
  }

  return {
    ...sourceSpec,
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
    })
    const translatedSubtitle = heroBlock.subtitle
      ? await translateText(heroBlock.subtitle, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      : undefined
    const translatedCtaLabel = heroBlock.cta_label
      ? await translateText(heroBlock.cta_label, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      : undefined

    return {
      ...heroBlock,
      title: translatedTitle.text,
      subtitle: translatedSubtitle?.text,
      cta_label: translatedCtaLabel?.text,
    }
  }

  if (blockType === 'section_title') {
    const titleBlock = block as any
    const translatedTitle = await translateText(titleBlock.title || '', {
      sourceLocale,
      targetLocale,
      glossary,
    })
    const translatedSubtitle = titleBlock.subtitle
      ? await translateText(titleBlock.subtitle, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      : undefined

    return {
      ...titleBlock,
      title: translatedTitle.text,
      subtitle: translatedSubtitle?.text,
    }
  }

  if (blockType === 'text') {
    const textBlock = block as any
    const translatedHeading = textBlock.heading
      ? await translateText(textBlock.heading, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      : undefined
    const translatedBody = await translateText(textBlock.body || '', {
      sourceLocale,
      targetLocale,
      glossary,
    })

    return {
      ...textBlock,
      heading: translatedHeading?.text,
      body: translatedBody.text,
    }
  }

  if (blockType === 'bullets') {
    const bulletsBlock = block as any
    const translatedHeading = bulletsBlock.heading
      ? await translateText(bulletsBlock.heading, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      : undefined
    
    const translatedItems: string[] = []
    for (const item of bulletsBlock.items || []) {
      const translatedItem = await translateText(item, {
        sourceLocale,
        targetLocale,
        glossary,
      })
      translatedItems.push(translatedItem.text)
    }

    return {
      ...bulletsBlock,
      heading: translatedHeading?.text,
      items: translatedItems,
    }
  }

  if (blockType === 'footer') {
    const footerBlock = block as any
    const translatedCompanyName = await translateText(footerBlock.company_name || '', {
      sourceLocale,
      targetLocale,
      glossary,
    })
    const translatedAddress = footerBlock.address
      ? await translateText(footerBlock.address, {
          sourceLocale,
          targetLocale,
          glossary,
        })
      : undefined

    return {
      ...footerBlock,
      company_name: translatedCompanyName.text,
      address: translatedAddress?.text,
    }
  }

  // For other block types, return as-is (no text to translate)
  return block
}

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { moduleId, sourceLocale, targetLocales, mode } = translateModuleSchema.parse(body)

    // Load module
    const module = await prisma.emailModule.findUnique({
      where: { id: moduleId },
    })

    if (!module) {
      return NextResponse.json({ error: 'Module not found' }, { status: 404 })
    }

    // Only translate if VALIDATED
    if (module.status !== 'VALIDATED') {
      return NextResponse.json(
        { error: 'Only VALIDATED modules can be translated' },
        { status: 400 }
      )
    }

    // Get source spec
    const sourceSpec = module.spec as unknown as EmailSpec

    // Get glossary
    const glossary = await getGlossary()

    const translated: string[] = []
    const skipped: string[] = []

    // Translate for each target locale
    for (const targetLocale of targetLocales) {
      try {
        // Check if translation already exists
        const existing = await prisma.emailModuleI18n.findUnique({
          where: {
            moduleId_locale: {
              moduleId,
              locale: targetLocale,
            },
          },
        })

        if (existing && mode === 'missing') {
          skipped.push(targetLocale)
          continue
        }

        // Translate spec
        const translatedSpec = await translateModuleSpec(
          sourceSpec,
          targetLocale,
          sourceLocale,
          glossary
        )

        // Create or update translation
        await prisma.emailModuleI18n.upsert({
          where: {
            moduleId_locale: {
              moduleId,
              locale: targetLocale,
            },
          },
          create: {
            moduleId,
            locale: targetLocale,
            spec: translatedSpec as any,
            translationStatus: 'MACHINE',
          },
          update: {
            spec: translatedSpec as any,
            translationStatus: 'MACHINE',
          },
        })

        // Log translation
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.EMAIL_MODULE,
            entityId: moduleId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.SUCCESS,
            model: OPENAI_MODEL,
          },
        })

        translated.push(targetLocale)
      } catch (error: any) {
        console.error(`Error translating module to ${targetLocale}:`, error)
        
        // Log error
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.EMAIL_MODULE,
            entityId: moduleId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.ERROR,
            errorMessage: error.message || String(error),
            model: OPENAI_MODEL,
          },
        }).catch(() => {}) // Ignore log errors
      }
    }

    return NextResponse.json({
      translated,
      skipped,
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error translating email module:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









