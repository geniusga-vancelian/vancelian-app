'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowLeft, BookOpen, ClipboardCopy, Loader2 } from 'lucide-react'

type FixState = 'idle' | 'running' | 'success' | 'error'

const CMD = 'make doctor-fix'

type Capabilities = {
  canExecute: boolean
  reasonCode: string | null
  message: string | null
  command: string
  context: {
    nodeEnv: string
    host: string
    hostAllowed: boolean
    isDev: boolean
    vercel: boolean
    hasSession: boolean
    monorepoRootFound: boolean
    cwd: string
  }
}

export default function LocalGuidePage() {
  const router = useRouter()
  const [authChecked, setAuthChecked] = useState(false)
  const [capLoading, setCapLoading] = useState(true)
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [fixState, setFixState] = useState<FixState>('idle')
  const [fixMessage, setFixMessage] = useState<string | null>(null)
  const [fixOutput, setFixOutput] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login?redirect=/guide')
        } else {
          setAuthChecked(true)
        }
      })
      .catch(() => {
        router.push('/admin/login?redirect=/guide')
      })
  }, [router])

  useEffect(() => {
    if (!authChecked) return
    setCapLoading(true)
    fetch('/api/dev/local-doctor-fix')
      .then((r) => r.json())
      .then((data: Capabilities) => setCapabilities(data))
      .catch(() =>
        setCapabilities({
          canExecute: false,
          reasonCode: 'FETCH_ERROR',
          message: 'Impossible de vérifier les prérequis. Utilisez « Copier la commande ».',
          command: CMD,
          context: {
            nodeEnv: '',
            host: '',
            hostAllowed: false,
            isDev: false,
            vercel: false,
            hasSession: false,
            monorepoRootFound: false,
            cwd: '',
          },
        })
      )
      .finally(() => setCapLoading(false))
  }, [authChecked])

  const copyCmd = useCallback(() => {
    void navigator.clipboard.writeText(CMD)
  }, [])

  const runFix = useCallback(async () => {
    if (!capabilities?.canExecute) return
    setFixState('running')
    setFixMessage(null)
    setFixOutput(null)
    try {
      const res = await fetch('/api/dev/local-doctor-fix', { method: 'POST' })
      const data = (await res.json()) as {
        ok?: boolean
        output?: string
        message?: string
        error?: string
        hint?: string
        exitCode?: number
      }
      const text =
        typeof data.output === 'string'
          ? data.output
          : data.message || data.error || JSON.stringify(data, null, 2)
      setFixOutput(text)
      if (!res.ok) {
        setFixState('error')
        setFixMessage(
          data.message ||
            data.error ||
            (res.status === 503
              ? 'Indisponible depuis ce mode d’exécution — utilisez le terminal à la racine du dépôt.'
              : `Erreur HTTP ${res.status}`)
        )
        return
      }
      if (data.ok) {
        setFixState('success')
        setFixMessage(data.hint ?? 'Terminé.')
      } else {
        setFixState('error')
        setFixMessage(
          data.hint
            ? `${data.hint} (code de sortie ${data.exitCode ?? '?'})`
            : `La commande s’est terminée avec une erreur (code ${data.exitCode ?? '?'}). Voir la sortie ci-dessous.`
        )
      }
    } catch (e) {
      setFixState('error')
      setFixMessage(e instanceof Error ? e.message : 'Erreur réseau')
    }
  }, [capabilities?.canExecute])

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-600">
        <Loader2 className="w-8 h-8 animate-spin" aria-hidden />
      </div>
    )
  }

  const canRun = capabilities?.canExecute === true
  const disabledReason = capabilities && !capabilities.canExecute ? capabilities.message : null

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <header className="bg-gray-900 text-white px-4 py-3 flex items-center justify-between gap-4 flex-wrap shadow">
        <div className="flex items-center gap-3">
          <BookOpen className="w-6 h-6 shrink-0" aria-hidden />
          <div>
            <h1 className="text-lg font-semibold">Guide local Arquantix</h1>
            <p className="text-xs text-gray-400">Fiche pratique — environnement de développement</p>
          </div>
        </div>
        <Link
          href="/admin"
          className="inline-flex items-center gap-2 text-sm text-gray-300 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour à l’admin
        </Link>
      </header>

      <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
        <p className="font-medium mb-2">Correctif local (automatique optionnel)</p>

        <div className="flex flex-wrap gap-2 mb-3" aria-label="Contraintes du bouton automatique">
          <span className="inline-flex items-center rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-semibold text-white">
            Local only
          </span>
          <span className="inline-flex items-center rounded-full bg-slate-700 px-2.5 py-0.5 text-xs font-semibold text-white">
            Dev only
          </span>
          <span className="inline-flex items-center rounded-full bg-emerald-800 px-2.5 py-0.5 text-xs font-semibold text-white">
            Session admin
          </span>
          <span className="inline-flex items-center rounded-full border border-emerald-700 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-900">
            Safe command: make doctor-fix
          </span>
        </div>

        <p className="text-amber-900/90 mb-3">
          Le bouton ci-dessous n’exécute rien de destructif (pas de <code className="bg-amber-100 px-1 rounded">down -v</code>).
          Il n’est actif que si le serveur Next tourne en <strong>mode développement</strong> sur <strong>localhost</strong>, avec une session admin, et si la racine du dépôt est visible (typique : <code className="bg-amber-100 px-1 rounded">npm run dev</code> depuis le dossier web).
        </p>

        {capLoading && (
          <p className="flex items-center gap-2 text-amber-800/90 mb-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Vérification des prérequis…
          </p>
        )}

        {!capLoading && disabledReason && (
          <div
            className="mb-3 rounded-md border border-amber-400 bg-amber-100/80 px-3 py-2 text-amber-950"
            role="status"
          >
            <strong className="block text-sm mb-0.5">Bouton désactivé</strong>
            <span className="text-sm">{disabledReason}</span>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={runFix}
            disabled={fixState === 'running' || capLoading || !canRun}
            title={
              !canRun && disabledReason ? disabledReason : 'Lancer make doctor-fix sur la machine (prérequis OK)'
            }
            className="inline-flex items-center gap-2 rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {fixState === 'running' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Exécution…
              </>
            ) : (
              'Fix my local env'
            )}
          </button>
          <button
            type="button"
            onClick={copyCmd}
            className="inline-flex items-center gap-2 rounded-md border border-amber-300 bg-white px-3 py-2 text-sm text-amber-950 hover:bg-amber-100"
          >
            <ClipboardCopy className="w-4 h-4" />
            Copier la commande
          </button>
        </div>
        <p className="mt-2 text-xs text-amber-900/80">
          <strong>Toujours disponible :</strong> copiez <code className="bg-amber-100 px-1 rounded">{CMD}</code> dans un terminal à la racine du dépôt si le bouton est désactivé (Docker, production, etc.).
        </p>

        {fixState === 'success' && (
          <p className="mt-2 text-green-800 font-medium" role="status">
            Succès — voir la sortie ci-dessous.
          </p>
        )}
        {fixState === 'error' && fixMessage && (
          <p className="mt-2 text-red-800 font-medium" role="alert">
            {fixMessage}
          </p>
        )}
        {fixOutput && (
          <pre className="mt-3 max-h-64 overflow-auto rounded bg-gray-900 p-3 text-xs text-gray-100 whitespace-pre-wrap">
            {fixOutput}
          </pre>
        )}
      </div>

      <div className="flex-1 p-2 sm:p-4">
        <iframe
          title="Guide local Arquantix — fiche HTML"
          src="/guides/arquantix-local-operating.html"
          className="w-full h-[calc(100vh-14rem)] min-h-[480px] rounded-lg border border-gray-200 bg-white shadow-sm"
        />
      </div>
    </div>
  )
}
