import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const backendUrl = buildBackendUrl(`/api/chatbot/session/${encodeURIComponent(id)}`)
    const response = await fetch(backendUrl)
    const data = await response.json()
    if (!response.ok) return NextResponse.json(data, { status: response.status })
    return NextResponse.json(data)
  } catch (e: any) {
    return NextResponse.json({ error: e?.message || 'Internal error' }, { status: 500 })
  }
}
