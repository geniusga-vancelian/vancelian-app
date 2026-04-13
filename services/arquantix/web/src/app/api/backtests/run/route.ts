import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'
import { z } from 'zod'

const backtestCreateSchema = z.object({
  name: z.string().optional(),
  start_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
  end_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
  instrument_ids: z.array(z.number()).optional(),
  bundle_id: z.string().optional(),
  strategy: z.object({
    type: z.enum(['equal_weight', 'momentum', 'bundle_strategy', 'CPPI', 'CORE_SATELLITE']),
    params: z.object({
      lookback_days: z.number().int().min(1).max(252).optional(),
      floor_ratio: z.number().min(0).max(1).optional(),
      multiplier: z.number().min(0).optional(),
      risky_cap: z.number().min(0).max(1).optional(),
      core_min: z.number().min(0).max(1).optional(),
      core_yield: z.number().min(0).optional(),
      day_count: z.number().int().min(1).optional(),
      debug: z.boolean().optional(),
      // Core-Satellite params (V1 + V2 + V2.1)
      target_te: z.number().min(0).max(1).optional(),
      te_tolerance: z.number().min(0).optional(),
      te_max_hard_mult: z.number().min(1).optional(),
      lookback_risk_days: z.number().int().min(5).optional(),
      lookback_return_days: z.number().int().min(5).optional(),
      max_weight_per_asset: z.number().min(0).max(1).optional(),
      core_grid_step: z.number().min(0).max(1).optional(),
      top_k_satellite: z.number().int().min(1).optional(),
      // V2 params
      sat_min: z.number().min(0).max(1).optional(),
      shrinkage: z.boolean().optional(),
      turnover_penalty: z.number().min(0).optional(),
      stability_penalty: z.number().min(0).optional(),
      optimization_method: z.enum(['grid', 'quadratic']).optional(),
      // V2.1 EDHEC-style allocation params
      allocation_mode: z.enum(['te_target', 'utility_lambda', 'dynamic_cushion']).optional(),
      lambda_risk: z.number().min(0).optional(),
      floor_rel_ratio: z.number().min(0).max(1).optional(),
      floor_accrues_with_core: z.boolean().optional(),
      sat_max: z.number().min(0).max(1).optional(),
    }).optional(),
  }),
  rebalance: z.enum(['daily', 'weekly', 'monthly']),
  fees_bps: z.number().min(0).max(1000),
  slippage_bps: z.number().min(0).max(1000),
  allow_weekend_trading: z.boolean(),
}).refine(
  (data) => data.instrument_ids && data.instrument_ids.length > 0 || data.bundle_id,
  { message: 'Either instrument_ids or bundle_id must be provided' }
)

// POST /api/backtests/run - Run a backtest
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = backtestCreateSchema.parse(body)

    const backendUrl = buildBackendUrl('/api/backtests/run')

    try {
      const signed = await signAdminBackendJwtFromSession(session)
      if (!signed.ok) {
        return NextResponse.json(
          { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
          { status: 403 }
        )
      }
      const token = signed.token

      const backendResponse = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(validated),
      })

      if (!backendResponse.ok) {
        const errorText = await backendResponse.text()
        let errorData
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { error: errorText || 'Backend error' }
        }

        const errorMsg = errorData.detail || errorData.error || errorData.message || `Backend request failed (${backendResponse.status})`
        return NextResponse.json(
          {
            error: typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg),
            code: 'BACKEND_ERROR',
            status: backendResponse.status,
            backend_body: errorText.substring(0, 500),
          },
          { status: backendResponse.status }
        )
      }

      const result = await backendResponse.json()
      return NextResponse.json(result, { status: 200 })
    } catch (error: any) {
      if (error instanceof z.ZodError) {
        return NextResponse.json(
          { error: 'Invalid request data', details: error.issues },
          { status: 400 }
        )
      }

      console.error('[Backtest Run] Backend proxy error:', {
        message: error.message,
        url: backendUrl,
      })

      const isConnectionError =
        error.message?.includes('fetch failed') ||
        error.code === 'ECONNREFUSED' ||
        error.code === 'ECONNRESET' ||
        error.code === 'ETIMEDOUT'

      const errorMsg = isConnectionError
        ? `Backend is unavailable. Please ensure the FastAPI backend is running on ${backendUrl}`
        : (error.message || 'Backend request failed')

      return NextResponse.json(
        {
          error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg),
          code: isConnectionError ? 'BACKEND_UNAVAILABLE' : 'BACKEND_ERROR',
          url: backendUrl,
        },
        { status: 502 }
      )
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Backtest run error:', error)
    const errorMsg = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json(
      { error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg) },
      { status: 500 }
    )
  }
}
