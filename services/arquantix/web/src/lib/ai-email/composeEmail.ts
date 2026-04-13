/**
 * Compose email from prompt using OpenAI
 * Similar to translateText but for email generation
 */
import { openai, OPENAI_MODEL } from '@/lib/openai/client'
import { requestWithRetry } from '@/lib/openai/requestWithRetry'
import { EmailSpec } from '@/components/ai-email/types'
import { EmailSpecSchema } from '@/components/ai-email/schema'

const SYSTEM_PROMPT = `You are an Email Architect AI assistant. Your role is to generate professional, premium fintech email designs.

CRITICAL RULES:
1. You MUST return ONLY valid JSON conforming to the EmailSpec schema. No markdown, no explanations outside JSON.
2. You can ONLY use these block types: hero, text, feature_cards, cta, footer
3. Maximum 6 blocks total
4. Maximum 1 hero block
5. Footer block MUST be last and MUST include {{unsubscribe_url}} placeholder
6. Style: Premium fintech, clean, concise, professional
7. Subject line: Clear, action-oriented, max 200 chars
8. Preheader: Short preview text, max 150 chars
9. All text must be concise and professional
10. Feature cards: Maximum 3 items
11. CTA buttons: Clear, action-oriented labels

EmailSpec JSON Structure:
{
  "subject": "string (required, 1-200 chars)",
  "preheader": "string (optional, max 150 chars)",
  "locale": "string (2-letter code, default: en)",
  "blocks": [
    {
      "type": "hero",
      "title": "string (required)",
      "subtitle": "string (optional)",
      "image_url": "string (optional)",
      "cta_label": "string (optional)",
      "cta_url": "string (optional)"
    },
    {
      "type": "text",
      "heading": "string (optional)",
      "body": "string (required, 1-2000 chars)"
    },
    {
      "type": "feature_cards",
      "heading": "string (optional)",
      "items": [
        {
          "title": "string (required, 1-100 chars)",
          "body": "string (required, 1-300 chars)",
          "icon": "string (optional)"
        }
      ]
    },
    {
      "type": "cta",
      "label": "string (required, 1-50 chars)",
      "url": "string (required)",
      "hint": "string (optional, max 200 chars)"
    },
    {
      "type": "footer",
      "company_name": "string (required, 1-100 chars)",
      "address": "string (optional, max 500 chars)",
      "unsubscribe_url_placeholder": "{{unsubscribe_url}}"
    }
  ]
}

Remember: Return ONLY the JSON object, nothing else.`

function buildUserPrompt(userInput: string, previousSpec: EmailSpec | null, locale: string): string {
  let prompt = `Create a professional email in ${locale} locale based on this request:\n\n${userInput}\n\n`
  
  if (previousSpec) {
    prompt += "\nPrevious email structure (you can modify or rebuild):\n"
    prompt += `Subject: ${previousSpec.subject}\n`
    prompt += `Blocks: ${previousSpec.blocks.length}\n`
    prompt += "You can iterate on this design or create a new one based on the new request.\n"
  }
  
  prompt += "\nReturn ONLY the EmailSpec JSON object, no markdown, no code blocks, no explanations."
  
  return prompt
}

export async function composeEmailSpec(
  prompt: string,
  previousSpec: EmailSpec | null,
  locale: string = 'en'
): Promise<{ spec: EmailSpec; assistantText: string }> {
  const userPrompt = buildUserPrompt(prompt, previousSpec, locale)
  
  try {
    const response = await requestWithRetry(
      () =>
        openai.chat.completions.create({
          model: OPENAI_MODEL,
          messages: [
            { role: 'system', content: SYSTEM_PROMPT },
            { role: 'user', content: userPrompt },
          ],
          temperature: 0.3,
          max_tokens: 2000,
          response_format: { type: 'json_object' },
        }),
      'composeEmailSpec'
    )
    
    const content = response.choices[0]?.message?.content?.trim()
    if (!content) {
      throw new Error('No content returned from OpenAI')
    }
    
    // Parse JSON (might be wrapped in markdown)
    let jsonStr = content.trim()
    if (jsonStr.startsWith('```json')) {
      jsonStr = jsonStr.slice(7)
    }
    if (jsonStr.startsWith('```')) {
      jsonStr = jsonStr.slice(3)
    }
    if (jsonStr.endsWith('```')) {
      jsonStr = jsonStr.slice(0, -3)
    }
    jsonStr = jsonStr.trim()
    
    // Find JSON object
    const start = jsonStr.indexOf('{')
    const end = jsonStr.lastIndexOf('}') + 1
    if (start < 0 || end <= start) {
      throw new Error('No valid JSON found in response')
    }
    
    const specDict = JSON.parse(jsonStr.slice(start, end))
    const spec = EmailSpecSchema.parse(specDict) as EmailSpec
    
    return {
      spec,
      assistantText: "I've created a professional email with the requested content.",
    }
  } catch (error: any) {
    console.error('OpenAI email composition error:', {
      message: error.message,
      name: error.name,
      code: error.code,
      status: error.status,
      statusText: error.statusText,
      stack: error.stack?.split('\n').slice(0, 5).join('\n')
    })
    
    // If it's a clear API key issue, throw it instead of falling back
    if (error.message?.includes('api key') || error.message?.includes('OPENAI_API_KEY') || error.status === 401) {
      throw new Error(`OpenAI API key error: ${error.message}`)
    }
    
    // If it's a rate limit or quota issue, throw it
    if (error.status === 429 || error.message?.includes('rate limit') || error.message?.includes('quota')) {
      throw new Error(`OpenAI rate limit/quota error: ${error.message}`)
    }
    
    // For other errors, fallback to minimal spec
    console.warn('Falling back to minimal email spec due to OpenAI error')
    return createFallbackSpec(prompt, locale)
  }
}

function createFallbackSpec(prompt: string, locale: string): { spec: EmailSpec; assistantText: string } {
  const subject = prompt.split('.')[0].slice(0, 50) || 'New Email'
  
  const spec: EmailSpec = {
    subject,
    locale,
    blocks: [
      {
        type: 'hero',
        title: 'Welcome',
        subtitle: 'Thank you for your interest',
        cta_label: 'Learn More',
        cta_url: '#',
      },
      {
        type: 'text',
        heading: 'Content',
        body: prompt.slice(0, 500),
      },
      {
        type: 'footer',
        company_name: 'Company',
        unsubscribe_url_placeholder: '{{unsubscribe_url}}',
      },
    ],
  }
  
  return {
    spec,
    assistantText: "I've created a basic email structure. Please refine your request for a more customized design.",
  }
}

