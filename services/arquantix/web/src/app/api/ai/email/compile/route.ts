import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { compileMjml } from '@/lib/ai-email/compileMjml'

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { mjml } = body

    if (!mjml || typeof mjml !== 'string') {
      return NextResponse.json(
        { error: 'MJML content is required' },
        { status: 400 }
      )
    }

    const result = await compileMjml(mjml)
    return NextResponse.json(result)
  } catch (error: any) {
    console.error('Error compiling MJML:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to compile MJML' },
      { status: 500 }
    )
  }
}









