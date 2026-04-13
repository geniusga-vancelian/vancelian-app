/**
 * Validations au démarrage du runtime Node Next (instrumentation).
 *
 * - `BFF_ANONYMOUS_BACKEND_ADMIN_ID` : entier obligatoire (voir `backend-jwt.ts`).
 * - Optionnel : vérifier que la ligne existe dans `admin_users` (sauf si skip explicite).
 *
 * Désactiver la vérif DB (ex. `next build` sans Postgres) :
 * `SKIP_BFF_ANONYMOUS_ADMIN_DB_CHECK=1`
 */

import { parseRequiredAnonymousBackendAdminIdFromEnv } from '@/lib/backend-jwt'

function isNextProductionBuildPhase(): boolean {
  return process.env.NEXT_PHASE === 'phase-production-build'
}

export async function validateBffStartupConfig(): Promise<void> {
  const id = parseRequiredAnonymousBackendAdminIdFromEnv()

  if (process.env.SKIP_BFF_ANONYMOUS_ADMIN_DB_CHECK === '1') {
    console.warn(
      '[BFF] SKIP_BFF_ANONYMOUS_ADMIN_DB_CHECK=1 — skipping admin_users row validation for BFF_ANONYMOUS_BACKEND_ADMIN_ID'
    )
    return
  }

  if (isNextProductionBuildPhase()) {
    return
  }

  if (!process.env.DATABASE_URL?.trim()) {
    console.warn(
      '[BFF] DATABASE_URL absent — skip vérification admin_users pour BFF_ANONYMOUS_BACKEND_ADMIN_ID'
    )
    return
  }

  const { prisma } = await import('@/lib/prisma')
  const row = await prisma.adminUser.findUnique({ where: { id } })
  if (!row) {
    throw new Error(
      `[BFF] FATAL: admin_users.id=${id} (BFF_ANONYMOUS_BACKEND_ADMIN_ID) does not exist — create a dedicated technical admin row or fix the env`
    )
  }
}
