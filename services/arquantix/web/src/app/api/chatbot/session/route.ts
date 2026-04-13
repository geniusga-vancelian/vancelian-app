import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'

async function parseJsonOrText(res: Response): Promise<object> {
  const text = await res.text()
  try {
    return text ? JSON.parse(text) : {}
  } catch {
    return { detail: text || 'Backend returned invalid JSON' }
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}))
    const backendUrl = buildBackendUrl('/api/chatbot/session')
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    })
    const data = await parseJsonOrText(response)
    if (!response.ok) return NextResponse.json(data, { status: response.status })
    return NextResponse.json(data)
  } catch (e: any) {
    return NextResponse.json({ error: e?.message || 'Internal error' }, { status: 500 })
  }
}
