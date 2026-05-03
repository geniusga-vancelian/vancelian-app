import { NextRequest, NextResponse } from 'next/server'
import { openai, OPENAI_MODEL } from '@/lib/openai/client'

export const maxDuration = 30

/**
 * @deprecated Route legacy non authentifiée et sans persistence — remplacée par
 * `/api/mobile/flutter/assistance/chat/turn` (proxy → FastAPI Python
 * `/api/app/assistance/chat/turn`). Conservée temporairement pour ne pas
 * casser les builds mobiles antérieures à la migration MVP D.0.1.
 *
 * À supprimer une fois la prod 100% sur la nouvelle route et après que la
 * télémetrie ait confirmé l'absence de trafic.
 */

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

/**
 * System prompt prepended à chaque conversation : force un rendu Markdown
 * compatible avec l'interpréteur Markdown du paragraphe d'article côté
 * Flutter (cf. `ArticleParagraphMarkdown`).
 *
 * - Titres `##` / `###` (jamais `#`, réservé au titre de bulle).
 * - Gras / italique / liens / listes / citations / tableaux / blocs code.
 * - Pas de HTML brut.
 * - Français, ton factuel et concis.
 */
const SYSTEM_PROMPT = `Tu réponds **toujours** en Markdown valide, en français.

Utilise selon les besoins :
- titres \`##\` et \`###\` (jamais \`#\`)
- gras \`**…**\`, italique \`*…*\`
- listes à puces \`- \` ou numérotées \`1. \`
- liens \`[texte](https://…)\`
- citations \`> …\` (avec attribution \`— Auteur\` sur la dernière ligne quand c'est pertinent)
- tableaux Markdown \`| col | col |\`
- blocs de code triple-backtick \`\`\` pour le code ou les extraits à recopier littéralement

Pas de HTML brut. Reste clair, factuel et concis.`

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => null)
    if (!body || !Array.isArray(body.messages)) {
      return NextResponse.json(
        { error: 'Body must contain messages array' },
        { status: 400 }
      )
    }
    const messages = body.messages as ChatMessage[]
    const valid = messages.every(
      (m) =>
        m &&
        typeof m.role === 'string' &&
        ['user', 'assistant', 'system'].includes(m.role) &&
        typeof m.content === 'string'
    )
    if (!valid) {
      return NextResponse.json(
        { error: 'Each message must have role (user|assistant|system) and content string' },
        { status: 400 }
      )
    }

    const completion = await openai.chat.completions.create({
      model: OPENAI_MODEL,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        ...messages.map((m) => ({ role: m.role, content: m.content })),
      ],
      temperature: 0.7,
    })

    const content =
      completion.choices?.[0]?.message?.content?.trim() ?? ''
    return NextResponse.json({ content })
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Internal error'
    console.error('Chat API error:', e)
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
