import { prisma } from '@/lib/prisma'
import type { TranslationGlossary } from './types'

/**
 * Get translation glossary from AppSettings
 */
export async function getGlossary(): Promise<TranslationGlossary | null> {
  try {
    const settings = await prisma.appSettings.findUnique({
      where: { id: 'default' },
    })

    if (!settings || !settings.translationGlossary) {
      return null
    }

    return settings.translationGlossary as TranslationGlossary
  } catch (error) {
    console.error('Error fetching glossary:', error)
    return null
  }
}


