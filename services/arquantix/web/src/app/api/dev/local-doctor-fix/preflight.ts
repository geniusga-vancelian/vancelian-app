import type { NextRequest } from 'next/server'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { getSessionFromCookie } from '@/lib/auth'

export const SAFE_COMMAND = 'make doctor-fix' as const

/**
 * Détecte la racine du monorepo (Makefile + scripts/doctor_fix.sh).
 */
export function findMonorepoRoot(): string | null {
  let dir = process.cwd()
  for (let i = 0; i < 10; i++) {
    const makefile = join(dir, 'Makefile')
    const script = join(dir, 'scripts', 'doctor_fix.sh')
    if (existsSync(makefile) && existsSync(script)) {
      return dir
    }
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return null
}

export function isLocalHost(host: string): boolean {
  const h = host.split(':')[0]?.replace(/^\[|\]$/g, '') ?? ''
  return h === 'localhost' || h === '127.0.0.1' || h === '::1'
}

export function isDevEnvironment(): boolean {
  return process.env.NODE_ENV === 'development'
}

export type BlockReasonCode =
  | 'VERCEL'
  | 'NOT_DEVELOPMENT'
  | 'HOST_NOT_LOCAL'
  | 'NO_SESSION'
  | 'NO_MONOREPO'
  | null

export interface LocalDoctorFixPreflight {
  vercel: boolean
  nodeEnv: string
  host: string
  hostAllowed: boolean
  isDev: boolean
  session: Awaited<ReturnType<typeof getSessionFromCookie>>
  cwd: string
  root: string | null
}

export async function runLocalDoctorFixPreflight(
  request: NextRequest
): Promise<LocalDoctorFixPreflight> {
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host') ?? ''
  const session = await getSessionFromCookie()
  const root = findMonorepoRoot()
  return {
    vercel: process.env.VERCEL === '1',
    nodeEnv: process.env.NODE_ENV ?? '',
    host,
    hostAllowed: isLocalHost(host),
    isDev: isDevEnvironment(),
    session,
    cwd: process.cwd(),
    root,
  }
}

export function getBlockReason(p: LocalDoctorFixPreflight): BlockReasonCode {
  if (p.vercel) return 'VERCEL'
  if (!p.isDev) return 'NOT_DEVELOPMENT'
  if (!p.hostAllowed) return 'HOST_NOT_LOCAL'
  if (!p.session) return 'NO_SESSION'
  if (!p.root) return 'NO_MONOREPO'
  return null
}

export function canExecuteDoctorFix(p: LocalDoctorFixPreflight): boolean {
  return getBlockReason(p) === null
}

/** Message utilisateur (UI) selon le code de blocage */
export function userMessageForReason(code: BlockReasonCode): string {
  switch (code) {
    case 'VERCEL':
      return 'Non disponible sur Vercel.'
    case 'NOT_DEVELOPMENT':
      return 'Réservé à npm run dev (NODE_ENV=development). En production ou Docker « next start », utilisez un terminal à la racine du dépôt.'
    case 'HOST_NOT_LOCAL':
      return 'Réservé à un accès localhost / 127.0.0.1. Ouvrez le guide depuis la machine locale.'
    case 'NO_SESSION':
      return 'Session admin requise. Reconnectez-vous.'
    case 'NO_MONOREPO':
      return 'La racine du dépôt (Makefile + scripts) est introuvable depuis ce processus — typique du conteneur Docker web. Lancez make doctor-fix dans un terminal à la racine du clone.'
    default:
      return ''
  }
}
