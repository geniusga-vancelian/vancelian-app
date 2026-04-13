import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const session_id = searchParams.get('session_id')
    if (!session_id) {
      return NextResponse.json({ error: 'session_id required' }, { status: 400 })
    }
    const backendUrl = buildBackendUrl(`/api/chatbot/profile?session_id=${encodeURIComponent(session_id)}`)
    const response = await fetch(backendUrl)
    const data = await response.json()
    if (!response.ok) return NextResponse.json(data, { status: response.status })
    return NextResponse.json(data)
  } catch (e: any) {
    return NextResponse.json({ error: e?.message || 'Internal error' }, { status: 500 })
  }
}
