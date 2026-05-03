import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'node:child_process'
import {
  SAFE_COMMAND,
  canExecuteDoctorFix,
  getBlockReason,
  runLocalDoctorFixPreflight,
  userMessageForReason,
} from './preflight'

export const runtime = 'nodejs'

const TIMEOUT_MS = 600_000

function logStructured(
  event: 'preflight' | 'blocked' | 'start' | 'done' | 'spawn_error',
  payload: Record<string, unknown>
) {
  const line = {
    ts: new Date().toISOString(),
    channel: 'local-doctor-fix',
    event,
    ...payload,
  }
  console.info(`[local-doctor-fix] ${JSON.stringify(line)}`)
}

/** GET : capacité d’exécuter le fix (pour désactiver le bouton côté UI sans deviner). */
export async function GET(request: NextRequest) {
  const p = await runLocalDoctorFixPreflight(request)
  const reason = getBlockReason(p)
  const allowed = canExecuteDoctorFix(p)

  logStructured('preflight', {
    method: 'GET',
    authorized: allowed,
    reasonCode: reason,
    nodeEnv: p.nodeEnv,
    host: p.host,
    hostAllowed: p.hostAllowed,
    isDev: p.isDev,
    vercel: p.vercel,
    hasSession: !!p.session,
    userId: p.session?.userId ?? null,
    monorepoRootFound: !!p.root,
    cwd: p.cwd,
    command: SAFE_COMMAND,
  })

  return NextResponse.json({
    canExecute: allowed,
    reasonCode: reason,
    message: reason ? userMessageForReason(reason) : null,
    command: SAFE_COMMAND,
    context: {
      nodeEnv: p.nodeEnv,
      host: p.host,
      hostAllowed: p.hostAllowed,
      isDev: p.isDev,
      vercel: p.vercel,
      hasSession: !!p.session,
      monorepoRootFound: !!p.root,
      cwd: p.cwd,
    },
  })
}

export async function POST(request: NextRequest) {
  const p = await runLocalDoctorFixPreflight(request)
  const reason = getBlockReason(p)

  logStructured('preflight', {
    method: 'POST',
    authorized: reason === null,
    reasonCode: reason,
    nodeEnv: p.nodeEnv,
    host: p.host,
    hostAllowed: p.hostAllowed,
    isDev: p.isDev,
    vercel: p.vercel,
    hasSession: !!p.session,
    userId: p.session?.userId ?? null,
    monorepoRootFound: !!p.root,
    cwd: p.cwd,
    command: `${SAFE_COMMAND} (cwd=monorepo root)`,
  })

  if (p.vercel) {
    logStructured('blocked', { reasonCode: 'VERCEL', userId: p.session?.userId ?? null })
    return NextResponse.json({ error: 'Not available on Vercel' }, { status: 403 })
  }
  if (!p.isDev) {
    logStructured('blocked', { reasonCode: 'NOT_DEVELOPMENT', userId: p.session?.userId ?? null })
    return NextResponse.json(
      {
        error: userMessageForReason('NOT_DEVELOPMENT'),
      },
      { status: 403 }
    )
  }
  if (!p.hostAllowed) {
    logStructured('blocked', { reasonCode: 'HOST_NOT_LOCAL', userId: p.session?.userId ?? null })
    return NextResponse.json({ error: userMessageForReason('HOST_NOT_LOCAL') }, { status: 403 })
  }
  if (!p.session) {
    logStructured('blocked', { reasonCode: 'NO_SESSION', userId: null })
    return NextResponse.json({ error: 'Non authentifié' }, { status: 401 })
  }
  if (!p.root) {
    logStructured('blocked', { reasonCode: 'NO_MONOREPO', userId: p.session.userId })
    return NextResponse.json(
      {
        ok: false,
        code: 'NO_MONOREPO',
        message: userMessageForReason('NO_MONOREPO'),
      },
      { status: 503 }
    )
  }

  const root = p.root
  const userId = p.session.userId

  logStructured('start', {
    userId,
    cwd: root,
    argv: ['make', 'doctor-fix'],
    timeoutMs: TIMEOUT_MS,
  })

  const t0 = Date.now()
  const output = await new Promise<{ exitCode: number; combined: string }>((resolve) => {
    const chunks: Buffer[] = []
    const proc = spawn('make', ['doctor-fix'], {
      cwd: root,
      env: { ...process.env, DRY_RUN: '0' },
      shell: false,
    })
    proc.stdout?.on('data', (d: Buffer) => chunks.push(Buffer.from(d)))
    proc.stderr?.on('data', (d: Buffer) => chunks.push(Buffer.from(d)))
    const timer = setTimeout(() => {
      proc.kill('SIGTERM')
    }, TIMEOUT_MS)
    proc.on('close', (code) => {
      clearTimeout(timer)
      const combined = Buffer.concat(chunks).toString('utf8')
      resolve({ exitCode: code ?? 1, combined })
    })
    proc.on('error', (err) => {
      clearTimeout(timer)
      logStructured('spawn_error', {
        userId,
        message: err instanceof Error ? err.message : String(err),
      })
      resolve({
        exitCode: 1,
        combined: `Erreur de lancement : ${err instanceof Error ? err.message : String(err)}`,
      })
    })
  })

  const ms = Date.now() - t0
  const ok = output.exitCode === 0

  logStructured('done', {
    userId,
    authorized: true,
    exitCode: output.exitCode,
    durationMs: ms,
    outputChars: output.combined.length,
    success: ok,
  })

  return NextResponse.json(
    {
      ok,
      exitCode: output.exitCode,
      output: output.combined.slice(-120_000),
      hint:
        'Action locale sûre — ne touche pas aux volumes : compose up idempotent + restart ciblé api/web si besoin (pas de down -v).',
    },
    { status: 200 }
  )
}
