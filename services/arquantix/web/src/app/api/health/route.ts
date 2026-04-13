import { NextResponse } from 'next/server'

/**
 * Health check endpoint - bypasses middleware (path starts with /api)
 * Returns immediately for load balancers and monitoring
 */
export async function GET() {
  return NextResponse.json({ status: 'ok' }, {
    status: 200,
    headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' },
  })
}
