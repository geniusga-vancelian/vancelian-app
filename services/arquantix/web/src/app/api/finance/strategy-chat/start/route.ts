import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'
import { z } from 'zod'

const startSchema = z.object({
  locale: z.string().optional(),
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const parsed = startSchema.parse(body)
    const backendUrl = buildBackendUrl('/api/finance/strategy-chat/start')

    const signed = await signAdminBackendJwtFromSession(session)
    if (!signed.ok) {
      return NextResponse.json(
        { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
        { status: 403 }
      )
    }
    const token = signed.token

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(parsed),
    })

    const data = await response.json()
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }

    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Finance strategy chat start proxy error:', error)
    if (error instanceof z.ZodError) {
      const detailsStr = error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join(', ')
      return NextResponse.json({ error: 'Invalid request data', details: detailsStr }, { status: 400 })
    }
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
