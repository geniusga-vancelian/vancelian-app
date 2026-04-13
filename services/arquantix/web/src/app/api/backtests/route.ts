import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { buildBackendUrl } from '@/lib/backend'

// GET /api/backtests - List backtests with filtering
export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies()
    const sessionCookie = cookieStore.get('session')?.value

    if (!sessionCookie) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Extract query parameters
    const searchParams = request.nextUrl.searchParams
    const params = new URLSearchParams()
    
    if (searchParams.get('status')) {
      params.append('status', searchParams.get('status')!)
    }
    if (searchParams.get('strategy_type')) {
      params.append('strategy_type', searchParams.get('strategy_type')!)
    }
    if (searchParams.get('q')) {
      params.append('q', searchParams.get('q')!)
    }
    if (searchParams.get('date_from')) {
      params.append('date_from', searchParams.get('date_from')!)
    }
    if (searchParams.get('date_to')) {
      params.append('date_to', searchParams.get('date_to')!)
    }
    if (searchParams.get('limit')) {
      params.append('limit', searchParams.get('limit')!)
    }
    if (searchParams.get('offset')) {
      params.append('offset', searchParams.get('offset')!)
    }

    const url = `${buildBackendUrl('/api/backtests')}?${params.toString()}`
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Cookie': `session=${sessionCookie}`,
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    })

    if (!response.ok) {
      const errorText = await response.text()
      let errorData: any
      try {
        errorData = JSON.parse(errorText)
      } catch {
        errorData = { detail: errorText || `Backend error (${response.status})` }
      }
      
      return NextResponse.json(
        { error: errorData.detail || errorData.message || `Backend error (${response.status})` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[API] GET /api/backtests error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
