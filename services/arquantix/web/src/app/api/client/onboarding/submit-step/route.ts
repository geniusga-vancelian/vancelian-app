import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { person_id, jurisdiction, step_id, values } = body

    if (!person_id || !jurisdiction || !step_id || !values) {
      return NextResponse.json(
        { error: 'person_id, jurisdiction, step_id, and values are required' },
        { status: 400 }
      )
    }

    const queryParams = new URLSearchParams({
      jurisdiction,
      purpose: 'KYC',
    })

    const backendPath = `/api/persons/${person_id}/onboarding/submit-step?${queryParams.toString()}`
    const backendUrl = buildBackendUrl(backendPath)

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        step_id,
        values,
      }),
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
    console.error('Submit step proxy error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
