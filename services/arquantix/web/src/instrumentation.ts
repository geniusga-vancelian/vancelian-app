export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    try {
      const { assertProductionSandboxDisabled } = await import('@/lib/productionSandboxGuard')
      assertProductionSandboxDisabled()
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      console.error('[STARTUP FATAL]', msg)
      process.exit(1)
    }

    try {
      const { logLombardProductionEnvValidation } = await import('@/lib/portal/lombard/lombardProdEnvValidation')
      logLombardProductionEnvValidation()
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      console.error('[STARTUP] Lombard prod env validation error:', msg)
    }

    try {
      const { validateBffStartupConfig } = await import('@/lib/bff-startup-validation')
      await validateBffStartupConfig()
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      console.error(
        '[STARTUP] Validation BFF / admin technique échouée — le site peut quand même démarrer ; certaines routes API BFF échoueront tant que la config n’est pas corrigée.\n',
        msg,
        '\nAstuces : vérifier BFF_ANONYMOUS_BACKEND_ADMIN_ID et la ligne dans admin_users ; ou SKIP_BFF_ANONYMOUS_ADMIN_DB_CHECK=1 en local.',
      )
      // Ne pas faire échouer tout le processus Next (évite écran blanc / aucune page servie).
    }

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

