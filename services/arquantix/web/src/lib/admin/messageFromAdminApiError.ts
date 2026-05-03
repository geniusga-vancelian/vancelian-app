/**
 * Réponse d'API admin 500 : inclut parfois prismaCode / prismaValidation
 * (cachés si on ne lit que `error`). Cette fonction concatène tous les
 * champs disponibles dans un message lisible pour l'utilisateur.
 *
 * Extrait de `/admin/articles/[id]/page.tsx` pour réutilisation
 * notamment dans la page modale `/admin/articles/[id]/add-block`.
 */
export function messageFromAdminApiError(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') return fallback
  const o = payload as Record<string, unknown>
  const head =
    typeof o.error === 'string' && o.error.length > 0 ? o.error : fallback
  const parts: string[] = [head]
  if (typeof o.prismaCode === 'string' && o.prismaCode) {
    parts.push(`(Prisma ${o.prismaCode})`)
  }
  if (typeof o.prismaValidation === 'string' && o.prismaValidation) {
    parts.push(o.prismaValidation)
  }
  if (typeof o.prismaMessage === 'string' && o.prismaMessage) {
    parts.push(o.prismaMessage)
  }
  if (typeof o.prismaInit === 'string' && o.prismaInit) {
    parts.push(o.prismaInit)
  }
  if (typeof o.message === 'string' && o.message) {
    parts.push(o.message)
  }
  if (o.prismaMeta != null) {
    try {
      const s = JSON.stringify(o.prismaMeta)
      if (s && s !== '{}') {
        parts.push(s.length > 500 ? `${s.slice(0, 500)}…` : s)
      }
    } catch {
      /* ignore */
    }
  }
  if (typeof o.details === 'string' && o.details) {
    parts.push(o.details)
  }
  if (typeof o.hint === 'string' && o.hint) {
    parts.push(o.hint)
  }
  if (Array.isArray(o.issues)) {
    const zodLines: string[] = []
    for (const issue of o.issues as Array<Record<string, unknown>>) {
      if (!issue || typeof issue !== 'object') continue
      const path = Array.isArray(issue.path) ? (issue.path as unknown[]).join('.') : ''
      const msg = typeof issue.message === 'string' ? issue.message : ''
      if (path && msg) zodLines.push(`${path}: ${msg}`)
      else if (msg) zodLines.push(msg)
    }
    if (zodLines.length > 0) parts.push(zodLines.join(' ; '))
  }
  return parts.join(' — ')
}
