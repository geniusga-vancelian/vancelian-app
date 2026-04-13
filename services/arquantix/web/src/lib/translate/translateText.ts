import { openai, OPENAI_MODEL, OPENAI_TRANSLATION_TEMPERATURE } from '@/lib/openai/client'
import { requestWithRetry } from '@/lib/openai/requestWithRetry'
import type { TranslationOptions, TranslationResult } from './types'

const LOCALE_NAMES: Record<string, string> = {
  fr: 'French',
  en: 'English',
  it: 'Italian',
}

export async function translateText(
  text: string,
  options: TranslationOptions
): Promise<TranslationResult> {
  const { sourceLocale, targetLocale, glossary } = options

  // Build glossary instructions
  let glossaryInstructions = ''
  if (glossary?.brandTerms && glossary.brandTerms.length > 0) {
    const terms = glossary.brandTerms.filter((t) => t.keep).map((t) => t.term)
    if (terms.length > 0) {
      glossaryInstructions += `\n\nIMPORTANT: Keep these brand terms unchanged: ${terms.join(', ')}`
    }
  }
  if (glossary?.preferred && glossary.preferred.length > 0) {
    const pairs = glossary.preferred.map((p) => `"${p.from}" → "${p.to}"`).join(', ')
    glossaryInstructions += `\n\nPreferred translations: ${pairs}`
  }

  const systemPrompt = `You are a professional translator. Translate the following text from ${LOCALE_NAMES[sourceLocale] || sourceLocale} to ${LOCALE_NAMES[targetLocale] || targetLocale}.

Rules:
- Maintain the same tone and style (premium, professional)
- Do not add or remove content
- Keep the same structure${glossaryInstructions}

Return ONLY the translated text, nothing else.`

  try {
    const response = await requestWithRetry(
      () =>
        openai.chat.completions.create({
          model: OPENAI_MODEL,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: text },
          ],
          temperature: OPENAI_TRANSLATION_TEMPERATURE,
          max_tokens: 2000,
        }),
      `translateText(${sourceLocale}→${targetLocale})`
    )

    const translated = response.choices[0]?.message?.content?.trim() || text
    const tokensUsed = response.usage?.total_tokens

    return {
      translated,
      text: translated,
      tokensUsed,
    }
  } catch (error) {
    console.error('OpenAI translation error:', error)
    throw new Error(`Translation failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

