import { NextRequest, NextResponse } from 'next/server'
import { openai, OPENAI_MODEL } from '@/lib/openai/client'

export const maxDuration = 30

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

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
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
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
