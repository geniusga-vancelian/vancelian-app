/**
 * Variables d’environnement requises pour l’API S3 compatible (Cloudflare R2).
 * Le dashboard Cloudflare utilise ta session ; l’app a besoin de jetons R2 (Manage R2 API Tokens).
 */

const REQUIRED = ['R2_ENDPOINT', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY'] as const

export function missingR2EnvVarNames(): string[] {
  return REQUIRED.filter((k) => {
    const v = process.env[k]
    return v === undefined || String(v).trim() === ''
  })
}

export function isR2Configured(): boolean {
  return missingR2EnvVarNames().length === 0
}

/**
 * Message d’erreur pour l’API / les logs (pas de secret dedans).
 */
export function r2CredentialsNotConfiguredMessage(): string {
  const miss = missingR2EnvVarNames()
  if (miss.length === 0) {
    return ''
  }
  return (
    `R2 credentials not configured (missing: ${miss.join(', ')}). ` +
    `The Cloudflare console uses your account login; this app needs R2 S3 API keys ` +
    `(R2 → Manage R2 API Tokens). With npm run dev: services/arquantix/web/.env.local ` +
    `or repo root .env (loaded via next.config.js). With Docker: repo root .env and/or .env.arquantix ` +
    `(compose env_file for arquantix-web).`
  )
}

export function assertR2Configured(): void {
  if (!isR2Configured()) {
    throw new Error(r2CredentialsNotConfiguredMessage())
  }
}
