/**
 * Variables d'environnement requises pour l'API S3 (AWS S3 prod ou Cloudflare R2 local).
 *
 * Le storage est désormais agnostique de provider : le code lit `STORAGE_*` en priorité
 * (production AWS S3) avec fallback sur `R2_*` (compat dev local Cloudflare R2).
 *
 * Les exports historiques (`isR2Configured`, `assertR2Configured`, etc.) sont conservés
 * pour ne pas casser les imports existants — ils opèrent désormais sur le couple agnostique.
 */

type Triplet = { endpoint: string; accessKeyId: string; secretAccessKey: string }

function readEnvTriplet(): Partial<Triplet> {
  const endpoint =
    process.env.STORAGE_ENDPOINT?.trim() || process.env.R2_ENDPOINT?.trim() || ''
  const accessKeyId =
    process.env.STORAGE_ACCESS_KEY_ID?.trim() || process.env.R2_ACCESS_KEY_ID?.trim() || ''
  const secretAccessKey =
    process.env.STORAGE_SECRET_ACCESS_KEY?.trim() ||
    process.env.R2_SECRET_ACCESS_KEY?.trim() ||
    ''
  return { endpoint, accessKeyId, secretAccessKey }
}

export function missingR2EnvVarNames(): string[] {
  const t = readEnvTriplet()
  const miss: string[] = []
  if (!t.endpoint) miss.push('STORAGE_ENDPOINT (or R2_ENDPOINT)')
  if (!t.accessKeyId) miss.push('STORAGE_ACCESS_KEY_ID (or R2_ACCESS_KEY_ID)')
  if (!t.secretAccessKey) miss.push('STORAGE_SECRET_ACCESS_KEY (or R2_SECRET_ACCESS_KEY)')
  return miss
}

export function isR2Configured(): boolean {
  return missingR2EnvVarNames().length === 0
}

/** Alias agnostique. */
export const isStorageConfigured = isR2Configured

/**
 * Message d'erreur pour l'API / les logs (pas de secret dedans).
 */
export function r2CredentialsNotConfiguredMessage(): string {
  const miss = missingR2EnvVarNames()
  if (miss.length === 0) {
    return ''
  }
  return (
    `Storage credentials not configured (missing: ${miss.join(', ')}). ` +
    `In prod we expect STORAGE_* (AWS S3) injected via Secrets Manager. ` +
    `In local dev with npm run dev: services/arquantix/web/.env.local or repo root .env. ` +
    `With Docker: repo root .env and/or .env.arquantix (compose env_file for arquantix-web).`
  )
}

export const storageCredentialsNotConfiguredMessage = r2CredentialsNotConfiguredMessage

export function assertR2Configured(): void {
  if (!isR2Configured()) {
    throw new Error(r2CredentialsNotConfiguredMessage())
  }
}

export const assertStorageConfigured = assertR2Configured

/** Détecte si le backend actuel est Cloudflare R2 (vs AWS S3 natif). */
export function isR2Backend(): boolean {
  const ep = process.env.STORAGE_ENDPOINT?.trim() || process.env.R2_ENDPOINT?.trim() || ''
  return /\.r2\.cloudflarestorage\.com/i.test(ep)
}
