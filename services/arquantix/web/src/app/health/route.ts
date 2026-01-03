import { NextResponse } from 'next/server'

export async function GET() {
  // Log simple pour diagnostic
  console.log('[HEALTH] Health check hit at', new Date().toISOString())
  
  return NextResponse.json(
    { 
      status: 'ok', 
      service: 'arquantix-coming-soon',
      timestamp: new Date().toISOString()
    },
    { status: 200 }
  )
}
