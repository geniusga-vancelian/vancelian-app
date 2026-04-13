import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

export async function GET(
  request: NextRequest,
  { params }: { params: { asset_class: string } }
) {
  const session = await getSessionFromCookie()
  if (!session || !session.userEmail) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const assetClass = params.asset_class
    const backendUrl = buildBackendUrl(`/api/bundles/asset-classes/${assetClass}/instruments`)

    const signed = await signAdminBackendJwtFromSession(session, {
      expiresIn: '1h',
    })
    if (!signed.ok) {
      return NextResponse.json(
        { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
        { status: 403 }
      )
    }
    const token = signed.token

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      let errorData
      try {
        errorData = JSON.parse(errorText)
      } catch {
        errorData = { error: errorText || 'Backend error' }
      }
      
      // Log error for debugging (first 500 chars)
      const errorPreview = JSON.stringify(errorData).substring(0, 500)
      console.error(`[Bundles Instruments] Backend error (${response.status}):`, errorPreview)
      
      return NextResponse.json(
        {
          error: errorData.detail || errorData.error || 'Backend request failed',
          backend_status: response.status,
          backend_body: errorData,
        },
        { status: response.status >= 400 && response.status < 500 ? response.status : 502 }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[Bundles Instruments] Proxy error:', {
      message: error.message,
      asset_class: params.asset_class,
      backend_url: buildBackendUrl(`/api/bundles/asset-classes/${params.asset_class}/instruments`),
    })
    
    const isConnectionError =
      error.message?.includes('fetch failed') ||
      error.code === 'ECONNREFUSED' ||
      error.code === 'ECONNRESET' ||
      error.code === 'ETIMEDOUT'
    
    const errorMsg = isConnectionError
      ? `Backend is unavailable. Please ensure the FastAPI backend is running.`
      : (error.message || 'Internal server error')
    
    return NextResponse.json(
      { error: errorMsg, code: isConnectionError ? 'BACKEND_UNAVAILABLE' : 'PROXY_ERROR' },
      { status: isConnectionError ? 502 : 500 }
    )
  }
}

