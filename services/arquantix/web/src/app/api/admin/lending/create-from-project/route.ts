import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { isProjectBasedExclusiveOfferCreationBlocked } from '@/lib/admin/projectExclusiveOfferGuards'
import { buildBackendUrl } from '@/lib/backend'

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      console.warn('[lending/create-from-project] No session')
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    if (isProjectBasedExclusiveOfferCreationBlocked()) {
      return NextResponse.json(
        {
          error: 'create-from-project disabled',
          detail:
            'Provision lending from a CMS Project is deprecated for Exclusive Offers. Use Packaged Product + create-from-packaged-product. Set ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO=true for rollback.',
          code: 'PROJECT_BASED_EO_BLOCKED',
        },
        { status: 403 },
      )
    }

    const body = await request.json()
    const upstream = buildBackendUrl('/api/lending/products/create-from-project')
    console.log('[lending/create-from-project] Proxying to backend:', {
      url: upstream,
      project_id: body.project_id,
      asset: body.asset,
      target_size: body.target_size,
    })

    const res = await fetch(upstream, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    let data: Record<string, unknown>
    const text = await res.text()
    try {
      data = JSON.parse(text)
    } catch {
      console.error('[lending/create-from-project] Non-JSON response:', text.slice(0, 500))
      return NextResponse.json(
        { detail: 'Backend returned non-JSON response' },
        { status: 502 }
      )
    }

    console.log('[lending/create-from-project] Backend responded:', res.status, data)
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[lending/create-from-project] Error:', error)
    return NextResponse.json(
      { detail: 'Backend unavailable — is the Python API running on port 8000?' },
      { status: 502 }
    )
  }
}
