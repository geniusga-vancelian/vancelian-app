'use client'

/**
 * Bandeau d'actions admin réutilisable « Vérifier la langue » /
 * « Corriger la langue » pour Footer / Menu / autres domains génériques.
 *
 * Encapsule :
 *   - Les 2 boutons (scan / apply).
 *   - La modale de progression (réutilise `AdminOperationProgressModal`).
 *   - L'orchestration des appels POST `scanUrl` / `applyUrl`.
 *   - La confirmation native bloquante avant un apply (`window.confirm`)
 *     pour éviter les écritures accidentelles (le footer/menu n'a pas de
 *     notion DRAFT/PUBLISHED).
 *
 * Utilisation type :
 *
 *   <LanguageCheckActions
 *     domainLabel="footer"
 *     scanUrl="/api/admin/site-footer/check-language/scan"
 *     applyUrl="/api/admin/site-footer/check-language/apply"
 *     activeLocale={activeLocale}
 *     localeLabel={LOCALE_LABEL[activeLocale]}
 *     onApplied={async () => { await reload() }}
 *   />
 */

import { useState } from 'react'
import { Languages, Sparkles } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  AdminOperationProgressModal,
  type AdminProgressStep,
} from '@/components/admin/AdminOperationProgressModal'
import {
  buildGenericApplySuccessModal,
  buildGenericScanSuccessModal,
  initialGenericApplyRunningSteps,
  initialGenericScanRunningSteps,
} from '@/components/admin/genericLanguageOpModalState'
import type { Locale } from '@/config/locales'

type Phase = 'running' | 'success' | 'error'

export type LanguageCheckActionsProps = {
  /** Libellé du domain affiché dans la modale (« footer », « menu »…). */
  domainLabel: string
  /** URL POST du scan (body `{ targetLocale }`). */
  scanUrl: string
  /** URL POST de l'apply (body `{ targetLocale }`). */
  applyUrl: string
  activeLocale: Locale
  /** Libellé lisible de la locale active (« Français », « English »…). */
  localeLabel: string
  /** Callback appelé après un apply réussi (rechargement des données). */
  onApplied?: () => void | Promise<void>
  /** Désactivation globale (loading parent, etc.). */
  disabled?: boolean
}

export function LanguageCheckActions({
  domainLabel,
  scanUrl,
  applyUrl,
  activeLocale,
  localeLabel,
  onApplied,
  disabled,
}: LanguageCheckActionsProps) {
  const [open, setOpen] = useState(false)
  const [phase, setPhase] = useState<Phase>('running')
  const [title, setTitle] = useState('')
  const [steps, setSteps] = useState<AdminProgressStep[]>([])
  const [summaryLines, setSummaryLines] = useState<string[]>([])
  const [errorMessage, setErrorMessage] = useState<string | undefined>()
  const [footerHint, setFooterHint] = useState<string | undefined>()

  const closeIfIdle = () => {
    if (phase === 'running') return
    setOpen(false)
  }

  const handleScan = async () => {
    setOpen(true)
    setPhase('running')
    setTitle(`Vérifier la langue (${localeLabel})`)
    setSteps(initialGenericScanRunningSteps(domainLabel, localeLabel))
    setSummaryLines([])
    setErrorMessage(undefined)
    setFooterHint(undefined)
    try {
      const res = await fetch(scanUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ targetLocale: activeLocale }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.error || `Scan failed (HTTP ${res.status})`)
      }
      const built = buildGenericScanSuccessModal(data, domainLabel, localeLabel)
      setSteps(built.steps)
      setSummaryLines(built.summaryLines)
      setPhase('success')
    } catch (e: unknown) {
      setPhase('error')
      setErrorMessage(e instanceof Error ? e.message : 'Erreur inconnue')
      setSummaryLines([`Le scan du ${domainLabel} a échoué.`])
    }
  }

  const handleApply = async () => {
    const confirmed = window.confirm(
      `Cette opération va modifier directement le ${domainLabel} en ${localeLabel} (pas de brouillon).\n\n` +
        `Les champs détectés comme étant dans une mauvaise langue seront retraduits via OpenAI.\n\n` +
        `Continuer ?`,
    )
    if (!confirmed) return

    setOpen(true)
    setPhase('running')
    setTitle(`Corriger la langue (${localeLabel})`)
    setSteps(initialGenericApplyRunningSteps(domainLabel, localeLabel))
    setSummaryLines([])
    setErrorMessage(undefined)
    setFooterHint(undefined)
    try {
      const res = await fetch(applyUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ targetLocale: activeLocale }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.error || `Apply failed (HTTP ${res.status})`)
      }
      const built = buildGenericApplySuccessModal(data, domainLabel, localeLabel)
      setSteps(built.steps)
      setSummaryLines(built.summaryLines)
      setFooterHint(built.footerHint)
      setPhase('success')
      if (onApplied) {
        try {
          await onApplied()
        } catch (e) {
          console.error('[LanguageCheckActions] onApplied threw:', e)
        }
      }
    } catch (e: unknown) {
      setPhase('error')
      setErrorMessage(e instanceof Error ? e.message : 'Erreur inconnue')
      setSummaryLines([`La correction du ${domainLabel} a échoué.`])
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleScan}
          disabled={disabled || open}
          className="bg-white"
        >
          <Languages className="mr-2 h-4 w-4" />
          Vérifier la langue ({localeLabel})
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleApply}
          disabled={disabled || open}
          className="bg-white"
        >
          <Sparkles className="mr-2 h-4 w-4" />
          Corriger la langue ({localeLabel})
        </Button>
      </div>

      <AdminOperationProgressModal
        open={open}
        title={title}
        subtitle={`Locale ${localeLabel} — ${domainLabel}`}
        phase={phase}
        steps={steps}
        summaryLines={summaryLines}
        errorMessage={errorMessage}
        footerHint={footerHint}
        onClose={closeIfIdle}
      />
    </>
  )
}
