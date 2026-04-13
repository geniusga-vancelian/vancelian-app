import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const category = searchParams.get('category')
    const isActive = searchParams.get('is_active')
    const search = searchParams.get('search')

    // Build query string
    const queryParams = new URLSearchParams()
    if (category) queryParams.set('category', category)
    if (isActive) queryParams.set('is_active', isActive)
    if (search) queryParams.set('search', search)

    const queryString = queryParams.toString()
    const backendPath = `/api/field-definitions${queryString ? `?${queryString}` : ''}`
    const backendUrl = buildBackendUrl(backendPath)

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || data.error || 'Backend error', status: response.status },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Field definitions proxy error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
