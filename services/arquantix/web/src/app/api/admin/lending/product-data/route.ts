import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const projectId = request.nextUrl.searchParams.get('project_id')
    if (!projectId) {
      return NextResponse.json({ error: 'project_id required' }, { status: 400 })
    }

    const res = await fetch(buildBackendUrl('/api/lending/products'), {
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    })

    if (!res.ok) {
      console.error('[lending/product-data] Backend returned', res.status)
      return NextResponse.json({ data: null })
    }

    const json = await res.json()
    const products = json.products || []

    const linked = products.find(
      (p: Record<string, unknown>) => p.project_id === projectId
    )

    if (!linked) {
      return NextResponse.json({ data: null })
    }

    const raised = Number(linked.current_raised || 0)
    const target = Number(linked.target_size || 0)

    return NextResponse.json({
      data: {
        lending_product_id: linked.product_id || linked.id,
        apy: linked.supply_apr != null
          ? Number(linked.supply_apr)
          : (linked.supply_apr_bps ? Number(linked.supply_apr_bps) / 100 : 0),
        raised,
        target,
        progress: target > 0 ? Number(((raised / target) * 100).toFixed(2)) : 0,
        investorsCount: linked.investors_count || 0,
        asset: linked.asset,
        status: linked.status,
        borrower_client_id: linked.borrower_client_id,
        pool_id: linked.pool_id || linked.lending_pool_id,
      },
    })
  } catch (error) {
    console.error('[lending/product-data] Error:', error)
    return NextResponse.json({ data: null })
  }
}
