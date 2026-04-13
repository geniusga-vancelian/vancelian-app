/**
 * Safe DB target for logs (no credentials).
 */
export function formatDatabaseUrlTarget(url: string | undefined): string {
  if (!url) return 'DATABASE_URL missing'
  try {
    const normalized = url.replace(/^postgresql(\+[a-z0-9]*)?:/i, 'http:')
    const u = new URL(normalized)
    const db = u.pathname.replace(/^\//, '') || '?'
    return `host=${u.hostname} port=${u.port || '5432'} db=${db}`
  } catch {
    return 'DATABASE_URL unparseable'
  }
}
