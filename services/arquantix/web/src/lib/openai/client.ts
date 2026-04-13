import OpenAI from 'openai'

if (!process.env.OPENAI_API_KEY) {
  throw new Error('OPENAI_API_KEY is not set in environment variables')
}

export const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
})

export const OPENAI_MODEL = process.env.OPENAI_MODEL || 'gpt-4o-mini'
export const OPENAI_TRANSLATION_TEMPERATURE = parseFloat(
  process.env.OPENAI_TRANSLATION_TEMPERATURE || '0'
)
export const OPENAI_TRANSLATION_MAX_CHARS = parseInt(
  process.env.OPENAI_TRANSLATION_MAX_CHARS || '12000',
  10
)


