/**
 * Variables d’environnement pour l’API S3 compatible (Cloudflare R2).
 * En prod ECS, les secrets sont souvent nommés STORAGE_* (alignés API Python) ;
 * en local / doc historique on utilise R2_* — les deux sont acceptés.
 */

function firstNonEmpty(...keys: string[]): string | undefined {
  for (const k of keys) {
    const v = process.env[k]
    if (v !== undefined && String(v).trim() !== '') {
      return String(v).trim()
    }
  }
  return undefined
}

export function getR2Endpoint(): string | undefined {
  return firstNonEmpty('R2_ENDPOINT', 'STORAGE_ENDPOINT')
}

export function getR2AccessKeyId(): string | undefined {
  return firstNonEmpty('R2_ACCESS_KEY_ID', 'STORAGE_ACCESS_KEY_ID')
}

export function getR2SecretAccessKey(): string | undefined {
  return firstNonEmpty('R2_SECRET_ACCESS_KEY', 'STORAGE_SECRET_ACCESS_KEY')
}

export function getR2BucketName(): string {
  return firstNonEmpty('R2_BUCKET_NAME', 'STORAGE_BUCKET_NAME') ?? 'arquantix-media'
}

export function getR2PublicUrl(): string | undefined {
  return firstNonEmpty('R2_PUBLIC_URL', 'STORAGE_PUBLIC_URL')
}

const REQUIRED_LABELS = ['R2_ENDPOINT', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY'] as const

export function missingR2EnvVarNames(): string[] {
  const miss: string[] = []
  if (!getR2Endpoint()) miss.push(REQUIRED_LABELS[0])
  if (!getR2AccessKeyId()) miss.push(REQUIRED_LABELS[1])
  if (!getR2SecretAccessKey()) miss.push(REQUIRED_LABELS[2])
  return miss
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
    `Provide R2_* or STORAGE_* (endpoint, access key id, secret) — e.g. Cloudflare R2 S3 API keys. ` +
    `Local: services/arquantix/web/.env.local or repo .env. ` +
    `ECS: map Secrets Manager to R2_* or the STORAGE_* keys already used by arquantix-web.`
  )
}

export function assertR2Configured(): void {
  if (!isR2Configured()) {
    throw new Error(r2CredentialsNotConfiguredMessage())
  }
}
