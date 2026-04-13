import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

export async function POST(request: NextRequest) {
  try {
    // Get session from cookie (same pattern as backtests/run)
    const session = await getSessionFromCookie()
    
    if (!session || !session.userEmail) {
      return NextResponse.json(
        { error: 'Unauthorized', session_found: false },
        { status: 401 }
      )
    }
    
    // Parse request body
    const body = await request.json()
    const validated = {
      days: body.days || 365,
      symbols: body.symbols || null,
      force: body.force || false,
    }
    
    const signed = await signAdminBackendJwtFromSession(session, {
      expiresIn: '1h',
    })
    if (!signed.ok) {
      return NextResponse.json(
        { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
        { status: 403 }
      )
    }
    const jwtToken = signed.token

    // Call backend
    const backendUrl = buildBackendUrl('/api/market-data/backfill-missing')
    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${jwtToken}`,
      },
      body: JSON.stringify(validated),
    })
    
    const backendStatus = backendResponse.status
    const backendBodyText = await backendResponse.text()
    let backendBody: any = {}
    try {
      backendBody = JSON.parse(backendBodyText)
    } catch {
      backendBody = { raw: backendBodyText.substring(0, 500) }
    }
    
    if (!backendResponse.ok) {
      return NextResponse.json(
        {
          error: 'Backend request failed',
          backend_status: backendStatus,
          backend_body: typeof backendBody === 'object' ? backendBody : { raw: String(backendBody).substring(0, 500) },
        },
        { status: backendStatus }
      )
    }
    
    return NextResponse.json(backendBody)
  } catch (error: any) {
    console.error('[market-data/backfill-missing] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', message: error.message },
      { status: 500 }
    )
  }
}

