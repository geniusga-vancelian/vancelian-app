import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const personId = searchParams.get('person_id')
    const jurisdiction = searchParams.get('jurisdiction')

    if (!personId || !jurisdiction) {
      return NextResponse.json(
        { error: 'person_id and jurisdiction are required' },
        { status: 400 }
      )
    }

    const queryParams = new URLSearchParams({
      jurisdiction,
      purpose: 'KYC',
    })

    const backendPath = `/api/persons/${personId}/onboarding/next-step?${queryParams.toString()}`
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
    console.error('Next step proxy error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
