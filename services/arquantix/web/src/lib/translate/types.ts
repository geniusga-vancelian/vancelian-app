export interface TranslationGlossary {
  brandTerms?: Array<{ term: string; keep: boolean }>
  preferred?: Array<{ from: string; to: string }>
}

export interface TranslationOptions {
  sourceLocale: string
  targetLocale: string
  glossary?: TranslationGlossary
  preserveFormatting?: boolean
}

export interface TranslationResult {
  translated: string
  /** Alias utilisé par les routes admin email / modules */
  text: string
  tokensUsed?: number
}


