import { openai, OPENAI_MODEL, OPENAI_TRANSLATION_TEMPERATURE, OPENAI_TRANSLATION_MAX_CHARS } from '@/lib/openai/client'
import { requestWithRetry } from '@/lib/openai/requestWithRetry'
import type { TranslationOptions, TranslationResult } from './types'

const LOCALE_NAMES: Record<string, string> = {
  fr: 'French',
  en: 'English',
  it: 'Italian',
}

/**
 * Split markdown by headings or paragraphs if too long
 */
function chunkMarkdown(text: string, maxChars: number): string[] {
  if (text.length <= maxChars) {
    return [text]
  }

  const chunks: string[] = []
  const lines = text.split('\n')
  let currentChunk = ''

  for (const line of lines) {
    // If adding this line would exceed maxChars, start a new chunk
    if (currentChunk.length + line.length + 1 > maxChars && currentChunk.length > 0) {
      chunks.push(currentChunk.trim())
      currentChunk = line + '\n'
    } else {
      currentChunk += line + '\n'
    }
  }

  if (currentChunk.trim().length > 0) {
    chunks.push(currentChunk.trim())
  }

  return chunks.length > 0 ? chunks : [text]
}

export async function translateMarkdown(
  markdown: string,
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

  const systemPrompt = `You are a professional translator. Translate the following Markdown text from ${LOCALE_NAMES[sourceLocale] || sourceLocale} to ${LOCALE_NAMES[targetLocale] || targetLocale}.

CRITICAL RULES:
- Preserve ALL Markdown formatting exactly (headings #, lists, links [text](url), code blocks \`\`\`, bold/italic, etc.)
- Only translate the text content, NOT the structure
- Keep code blocks and inline code unchanged
- Keep URLs unchanged
- Maintain the same tone and style (premium, professional)
- Do not add or remove content${glossaryInstructions}

Return ONLY the translated Markdown, nothing else.`

  // Chunk if too long
  const chunks = chunkMarkdown(markdown, OPENAI_TRANSLATION_MAX_CHARS)
  const translatedChunks: string[] = []
  let totalTokens = 0

  for (let i = 0; i < chunks.length; i++) {
    try {
      const response = await requestWithRetry(
        () =>
          openai.chat.completions.create({
            model: OPENAI_MODEL,
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: chunks[i] },
            ],
            temperature: OPENAI_TRANSLATION_TEMPERATURE,
            max_tokens: 4000,
          }),
        `translateMarkdown(${sourceLocale}→${targetLocale}, chunk ${i + 1}/${chunks.length})`
      )

      const translated = response.choices[0]?.message?.content?.trim() || chunks[i]
      translatedChunks.push(translated)
      totalTokens += response.usage?.total_tokens || 0
    } catch (error) {
      console.error('OpenAI translation error for chunk:', error)
      // Fallback: keep original chunk
      translatedChunks.push(chunks[i])
    }
  }

  const translated = translatedChunks.join('\n\n')
  return {
    translated,
    text: translated,
    tokensUsed: totalTokens,
  }
}

