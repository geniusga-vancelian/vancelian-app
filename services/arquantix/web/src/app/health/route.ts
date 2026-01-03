import { NextResponse } from 'next/server'

// Health check endpoint - no middleware, no redirects, instant response
export async function GET() {
  // Return 200 OK immediately, no JSON parsing needed
  return new NextResponse('ok', {
    status: 200,
    headers: {
      'Content-Type': 'text/plain',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
    },
  })
}
