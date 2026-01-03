export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { hostname, port } = process.env
    console.log(`[STARTUP] Next.js server starting...`)
    console.log(`[STARTUP] HOSTNAME: ${hostname || 'not set'}`)
    console.log(`[STARTUP] PORT: ${port || process.env.PORT || 'not set'}`)
    console.log(`[STARTUP] NODE_ENV: ${process.env.NODE_ENV}`)
    
    // Log when server is ready
    process.nextTick(() => {
      console.log(`[STARTUP] Server should be listening on ${hostname || '0.0.0.0'}:${port || process.env.PORT || 3000}`)
    })
  }
}

