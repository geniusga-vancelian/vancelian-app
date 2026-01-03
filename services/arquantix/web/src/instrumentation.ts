export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const hostname = process.env.HOSTNAME || process.env.HOST || '0.0.0.0'
    const port = process.env.PORT || '3000'
    
    console.log('='.repeat(60))
    console.log('[STARTUP] Next.js instrumentation registered')
    console.log(`[STARTUP] HOSTNAME: ${hostname}`)
    console.log(`[STARTUP] PORT: ${port}`)
    console.log(`[STARTUP] NODE_ENV: ${process.env.NODE_ENV}`)
    console.log(`[STARTUP] Listening address will be: http://${hostname}:${port}`)
    console.log('='.repeat(60))
  }
}

