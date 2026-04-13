import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { z } from 'zod'
import { buildBackendUrl } from '@/lib/backend'

const compareRequestSchema = z.object({
  run_ids: z.array(z.number().int().min(1)).min(1).max(10),
  align_mode: z.enum(['intersection', 'union']).optional().default('intersection'),
})

// POST /api/backtests/compare - Compare multiple backtests
export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies()
    const sessionCookie = cookieStore.get('session')?.value

    if (!sessionCookie) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    
    // Validate request body
    const validationResult = compareRequestSchema.safeParse(body)
    if (!validationResult.success) {
      return NextResponse.json(
        { error: 'Invalid request', details: validationResult.error.issues },
        { status: 400 }
      )
    }

    const url = buildBackendUrl('/api/backtests/compare')
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Cookie': `session=${sessionCookie}`,
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(validationResult.data),
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
    console.error('[API] POST /api/backtests/compare error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
