'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { MediaField } from '@/components/admin/MediaField'
import { toastError, toastSuccess, toastWarning } from '@/lib/admin/toast'
import { cn } from '@/lib/utils'

export type PrimaryNavLinkStatePayload = {
  status: 'unlinked' | 'content_page' | 'navigation_hub' | 'external_link'
  linkedCount: number
  multipleLinked: boolean
  menuItemIds: string[]
}

type Props = {
  slug: string
  initialNavMegaIconMediaId: string | null
  initialShowInMegaMenu: boolean
  primaryNavLinkState: PrimaryNavLinkStatePayload | undefined
  sectionsCount: number
  onSaved: () => void | Promise<void>
}

/**
 * Bloc « Page — hors traduction » : slug, mode page / hub, icône & visibilité méga-menu.
 */
export function PageNavMegaIconCard({
  slug,
  initialNavMegaIconMediaId,
  initialShowInMegaMenu,
  primaryNavLinkState,
  sectionsCount,
  onSaved,
}: Props) {
  const [navMegaIconMediaId, setNavMegaIconMediaId] = useState<string | null>(
    initialNavMegaIconMediaId,
  )
  const [showInMegaMenu, setShowInMegaMenu] = useState(initialShowInMegaMenu)
  const [saving, setSaving] = useState(false)
  const [modeSaving, setModeSaving] = useState(false)

  useEffect(() => {
    setNavMegaIconMediaId(initialNavMegaIconMediaId)
    setShowInMegaMenu(initialShowInMegaMenu)
  }, [initialNavMegaIconMediaId, initialShowInMegaMenu, slug])

  const nav = primaryNavLinkState ?? {
    status: 'unlinked' as const,
    linkedCount: 0,
    multipleLinked: false,
    menuItemIds: [],
  }

  const modeDisabled =
    nav.status === 'unlinked' ||
    nav.status === 'external_link' ||
    modeSaving ||
    saving

  const handleModeChange = async (mode: 'content_page' | 'navigation_hub') => {
    if (modeDisabled) return
    if (
      (mode === 'content_page' && nav.status === 'content_page') ||
      (mode === 'navigation_hub' && nav.status === 'navigation_hub')
    ) {
      return
    }
    setModeSaving(true)
    try {
      const res = await fetch(
        `/api/admin/pages/${encodeURIComponent(slug)}/navigation-mode`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ mode }),
        },
      )
      const data = (await res.json().catch(() => ({}))) as {
        ok?: boolean
        error?: string
        warnings?: string[]
      }
      if (!res.ok) {
        throw new Error(typeof data.error === 'string' ? data.error : 'Mise à jour impossible')
      }
      if (Array.isArray(data.warnings) && data.warnings.length > 0) {
        toastWarning(data.warnings.join(' '))
      }
      toastSuccess('Mode de navigation mis à jour')
      await onSaved()
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setModeSaving(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await fetch(
        `/api/admin/pages/${encodeURIComponent(slug)}/nav-mega-icon`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ navMegaIconMediaId, showInMegaMenu }),
        },
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(typeof data.error === 'string' ? data.error : 'Enregistrement impossible')
      }
      toastSuccess('Paramètres méga-menu enregistrés')
      await onSaved()
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  const isHub = nav.status === 'navigation_hub'
  const isContent = nav.status === 'content_page'

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-3xl space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div>
        <h2 className="text-sm font-semibold text-slate-900">Page — hors traduction</h2>
        <p className="mt-0.5 text-xs text-slate-600">
          Identifiant technique, mode menu primaire et média partagés par toutes les langues (hors
          sélecteur de langue ci-dessous).
        </p>
      </div>

      <div className="rounded-md border border-slate-100 bg-slate-50/80 px-3 py-2">
        <p className="text-[11px] font-medium text-slate-600">Slug</p>
        <p className="mt-0.5 font-mono text-sm text-slate-900">{slug}</p>
      </div>

      <div className="space-y-3 rounded-md border border-slate-100 bg-white px-3 py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs font-semibold text-slate-900">Mode de la page</h3>
          {nav.status === 'navigation_hub' ? (
            <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-800">
              Non cliquable dans le menu primaire
            </span>
          ) : null}
          {nav.status === 'content_page' ? (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-900">
              Page publique cliquable
            </span>
          ) : null}
          {nav.status === 'external_link' ? (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-950">
              Lien externe (menu)
            </span>
          ) : null}
        </div>

        {nav.status === 'unlinked' ? (
          <div className="rounded-md border border-amber-200 bg-amber-50/80 px-3 py-2 text-xs text-amber-950">
            <p className="font-medium">Non liée au menu primaire</p>
            <p className="mt-1 text-amber-900/90">
              Aucun item du menu niveau 1 ne pointe vers cette page. Liez-la depuis{' '}
              <Link href="/admin/pages" className="font-medium underline">
                la structure du site
              </Link>{' '}
              pour activer le mode Page / Hub.
            </p>
          </div>
        ) : null}

        {nav.status === 'external_link' ? (
          <div className="rounded-md border border-amber-200 bg-amber-50/80 px-3 py-2 text-xs text-amber-950">
            <p className="font-medium">Lien externe dans le menu</p>
            <p className="mt-1 text-amber-900/90">
              Le mode Page / Hub ne s’applique pas. Modifiez la configuration depuis l’éditeur de
              lien :{' '}
              {nav.menuItemIds[0] ? (
                <Link
                  href={`/admin/pages/nav-menu-link/${encodeURIComponent(nav.menuItemIds[0])}`}
                  className="font-medium underline"
                >
                  ouvrir l’éditeur de lien
                </Link>
              ) : (
                'structure du site'
              )}
              .
            </p>
          </div>
        ) : null}

        {nav.multipleLinked && nav.status !== 'unlinked' && nav.status !== 'external_link' ? (
          <p className="text-[11px] text-slate-600">
            Plusieurs entrées du menu primaire ciblent cette page : un changement de mode les
            synchronise toutes.
          </p>
        ) : null}

        <div
          className={cn(
            'flex rounded-lg border p-0.5',
            modeDisabled ? 'border-slate-100 bg-slate-50 opacity-70' : 'border-slate-200 bg-slate-50',
          )}
          role="group"
          aria-label="Mode de la page"
        >
          <button
            type="button"
            disabled={modeDisabled}
            onClick={() => void handleModeChange('content_page')}
            className={cn(
              'flex-1 rounded-md px-3 py-2 text-left text-sm font-medium transition-colors',
              isContent
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900',
            )}
          >
            Page avec contenu
          </button>
          <button
            type="button"
            disabled={modeDisabled}
            onClick={() => void handleModeChange('navigation_hub')}
            className={cn(
              'flex-1 rounded-md px-3 py-2 text-left text-sm font-medium transition-colors',
              isHub
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900',
            )}
          >
            Hub de navigation
          </button>
        </div>

        {isContent && nav.status !== 'unlinked' ? (
          <p className="text-[11px] leading-relaxed text-slate-600">
            Cette entrée est une <strong>vraie page</strong> publique : elle peut contenir des
            sections et être <strong>cliquable</strong> dans la navigation. Elle peut aussi ouvrir un
            méga-menu si au moins deux enfants visibles sont configurés.
          </p>
        ) : null}

        {isHub ? (
          <>
            <p className="text-[11px] leading-relaxed text-slate-600">
              Cette entrée sert à <strong>organiser le menu et le méga-menu</strong>. Elle n’a pas
              besoin de contenu et <strong>n’est pas cliquable</strong> dans la barre principale. Un
              méga-menu s’ouvre au survol si au moins <strong>deux</strong> enfants éligibles
              existent.
            </p>
            {sectionsCount > 0 ? (
              <div className="rounded-md border border-amber-200 bg-amber-50/60 px-3 py-2 text-[11px] text-amber-950">
                Cette page contient déjà des sections. Passer en hub <strong>ne supprime rien</strong>
                , mais l’item de menu ne mènera plus vers cette URL depuis la barre — le contenu reste
                accessible si vous publiez l’URL directement.
              </div>
            ) : null}
            <p className="text-[11px] text-slate-500">
              Sans sections publiées, l’URL directe reste en <strong>404</strong> (comportement CMS
              actuel).
            </p>
          </>
        ) : null}
      </div>

      <div>
        <MediaField
          label="Icône méga-menu (média)"
          value={navMegaIconMediaId}
          onChange={setNavMegaIconMediaId}
          allowClear
          preview
        />
        <p className="mt-1.5 text-[10px] text-slate-500">
          Utilisée lorsque cette page apparaît comme <strong>enfant</strong> dans le méga-menu
          d’un autre item. Même fichier pour toutes les langues.
        </p>
      </div>

      <label className="flex cursor-pointer items-start gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={showInMegaMenu}
          onChange={(e) => setShowInMegaMenu(e.target.checked)}
          className="mt-1 rounded border-slate-300"
        />
        <span>
          <span className="font-medium">Afficher cette page dans le méga-menu</span>
          <span className="mt-0.5 block text-xs text-slate-500">
            En tant qu’enfant d’un hub ou d’une page avec méga-menu. Décochez pour exclure du panneau
            tout en gardant la page dans la structure si besoin.
          </span>
        </span>
      </label>

      <div className="flex justify-end border-t border-slate-100 pt-3">
        <Button type="submit" disabled={saving || modeSaving}>
          {saving ? 'Enregistrement…' : 'Enregistrer icône & visibilité méga-menu'}
        </Button>
      </div>
    </form>
  )
}
