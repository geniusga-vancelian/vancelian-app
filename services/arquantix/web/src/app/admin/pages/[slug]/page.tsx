'use client'

import { useEffect, useMemo, useState, useCallback } from 'react'
import { useRouter, useParams, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  Languages,
  Wand2,
  Rocket,
  Eye,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { AdminEditingLocaleBar } from '@/components/admin/AdminEditingLocaleBar'
import { useAdminEditingLocale } from '@/components/admin/AdminEditingLocaleContext'
import { defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import {
  AdminOperationProgressModal,
  type AdminProgressStep,
} from '@/components/admin/AdminOperationProgressModal'
import {
  buildPageApplySuccessModal,
  buildPageScanSuccessModal,
  initialPageApplyRunningSteps,
  initialPageScanRunningSteps,
} from '@/components/admin/pageLanguageOpModalState'
import {
  buildPagePublishSuccessModal,
  initialPagePublishRunningSteps,
} from '@/components/admin/pagePublishOpModalState'
import {
  I18nFindingsTable,
  pageCheckReportAggregate,
  pageCheckReportToRows,
} from '@/components/admin/I18nFindingsTable'
import { PagePreviewPanel } from '@/components/admin/PagePreviewPanel'
import { PagePreviewDrawer } from '@/components/admin/PagePreviewDrawer'
import {
  computePageLocaleCompleteness,
  computeSectionContentLocaleCompleteness,
  type LocaleCompletenessLevel,
} from '@/lib/admin/pageLocaleCompleteness'
import { getSectionType, resolveCanonicalSectionKey } from '@/lib/sections/library'
import { LocaleCompletenessStrip } from '@/components/admin/LocaleCompletenessStrip'
import {
  PageLocaleMetadataForm,
  type PageLocaleMetadataInitial,
} from '@/components/admin/PageLocaleMetadataForm'
import {
  PageNavMegaIconCard,
  type PrimaryNavLinkStatePayload,
} from '@/components/admin/PageNavMegaIconCard'

/** Libellé catalogue + suffixe d’instance pour l’admin (liste modules, aperçu isolé). */
function formatAdminSectionDisplayLine(
  section: {
    key: string
    commonModuleRefId?: string | null
  },
  commonModuleCatalog: Record<string, { label: string }>,
): { line: string; tooltip: string } {
  const rawKey = section.key.trim()
  const sectionCanon = resolveCanonicalSectionKey(rawKey) ?? rawKey
  const refId = section.commonModuleRefId ?? null
  const typeMeta = getSectionType(rawKey)

  if (sectionCanon === 'common_module_ref') {
    const commonLabel = refId ? commonModuleCatalog[refId]?.label : null
    const fallbackLabel = typeMeta?.label ?? 'Module commun'
    const line = (commonLabel?.trim() || fallbackLabel).trim()
    const tooltip = [line, refId ? `ID : ${refId}` : null, `Clé : ${rawKey}`].filter(Boolean).join('\n')
    return { line, tooltip }
  }

  const base = typeMeta?.label ?? rawKey
  let instanceNum: string | null = null
  if (rawKey !== sectionCanon && !(rawKey === 'projects' && sectionCanon === 'project_grid')) {
    const esc = sectionCanon.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const m = rawKey.match(new RegExp(`^${esc}_(\\d+)$`))
    instanceNum = m ? m[1] : null
  }
  const line = instanceNum ? `${base} · ${instanceNum}` : base
  const tooltip = instanceNum ? `${base} (instance n°${instanceNum}) — ${rawKey}` : `${base} — ${rawKey}`
  return { line, tooltip }
}

interface Section {
  id: string
  key: string
  order: number
  schemaVersion: string
  /** Renseigné côté API pour les lignes `common_module_ref`. */
  commonModuleRefId?: string | null
  contents: Array<{
    id: string
    locale: string
    status: string
  }>
}

interface Page {
  id: string
  slug: string
  urlPath: string
  title: string | null
  template: string
  themeColor?: string
  description: string | null
  showInMegaMenu?: boolean
  navMegaIconMediaId?: string | null
  pageI18n?: Array<{
    locale: string
    title: string | null
    description: string | null
    navMegaCategory?: string | null
    navMegaDescription?: string | null
  }>
  primaryNavLinkState?: PrimaryNavLinkStatePayload
  /** Si non null, le bouton supprimer est désactivé (message explicatif). */
  deleteBlockedReason?: string | null
}

export default function AdminPageSectionsPage() {
  const router = useRouter()
  const params = useParams()
  const searchParams = useSearchParams()
  const { locale: editingLocale, setLocale: setEditingLocale } = useAdminEditingLocale()
  const slug = (params?.slug as string | undefined) ?? ''

  const [page, setPage] = useState<Page | null>(null)
  const [sections, setSections] = useState<Section[]>([])
  const [loading, setLoading] = useState(true)
  /** Après 404 API : évite la redirection aveugle vers /admin/pages (on affiche l’aide ici). */
  const [missingKind, setMissingKind] = useState<
    'article' | 'exclusiveOfferGabarit' | 'other' | null
  >(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [sectionToDelete, setSectionToDelete] = useState<string | null>(null)
  const [pageDeleteDialogOpen, setPageDeleteDialogOpen] = useState(false)
  const [pageCopyDialog, setPageCopyDialog] = useState<Locale | null>(null)

  // « Vérifier la langue » + « Corriger le brouillon » — alignement Vault Builder.
  const [checkLangBusy, setCheckLangBusy] = useState(false)
  const [checkLangApplyBusy, setCheckLangApplyBusy] = useState(false)
  const [publishBusy, setPublishBusy] = useState(false)
  const [checkLangReport, setCheckLangReport] = useState<
    (Record<string, unknown> & { mode?: 'scan' | 'afterApply' }) | null
  >(null)
  const [pageOpModal, setPageOpModal] = useState<{
    title: string
    subtitle?: string
    phase: 'running' | 'success' | 'error'
    steps: AdminProgressStep[]
    summaryLines: string[]
    errorMessage?: string
    footerHint?: string
  } | null>(null)

  const [previewLocale, setPreviewLocale] = useState<Locale>(editingLocale)
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'mobile'>('desktop')
  const [previewDrawerOpen, setPreviewDrawerOpen] = useState(false)
  const [previewReloadEpoch, setPreviewReloadEpoch] = useState(0)
  /** Aperçu iframe : module seul (sinon page entière). */
  const [narrowSectionPreviewId, setNarrowSectionPreviewId] = useState<string | null>(null)
  const [commonModuleCatalog, setCommonModuleCatalog] = useState<
    Record<string, { label: string; localeCompleteness: Record<Locale, LocaleCompletenessLevel> }>
  >({})

  useEffect(() => {
    const q = searchParams?.get('editingLocale')
    if (q && isValidLocale(q)) {
      setEditingLocale(q)
    }
  }, [searchParams, setEditingLocale])

  useEffect(() => {
    setPreviewLocale(editingLocale)
  }, [editingLocale])

  const bumpPreviewReload = useCallback(() => {
    setPreviewReloadEpoch((e) => e + 1)
  }, [])

  const fetchPageData = async () => {
    if (!slug) {
      setLoading(false)
      setMissingKind('other')
      return
    }

    setLoading(true)
    setMissingKind(null)
    try {
      const pageRes = await fetch(`/api/admin/pages/${slug}`)
      if (!pageRes.ok) {
        if (pageRes.status === 401) {
          router.push('/admin/login')
          return
        }
        if (pageRes.status === 404) {
          setPage(null)
          setSections([])
          setCommonModuleCatalog({})
          setMissingKind(
            slug === 'article'
              ? 'article'
              : slug === 'exclusive-offer'
                ? 'exclusiveOfferGabarit'
                : 'other',
          )
          return
        }
        throw new Error('Failed to fetch page')
      }
      const pageData = await pageRes.json()
      setPage(pageData.page)

      const sectionsRes = await fetch(`/api/admin/pages/${slug}/sections`)
      if (!sectionsRes.ok) {
        throw new Error('Failed to fetch sections')
      }
      const sectionsData = await sectionsRes.json()
      setSections(sectionsData.sections || [])

      const cmRes = await fetch('/api/admin/site-common-modules')
      if (cmRes.ok) {
        const cmJson = await cmRes.json()
        const cat: Record<
          string,
          { label: string; localeCompleteness: Record<Locale, LocaleCompletenessLevel> }
        > = {}
        if (Array.isArray(cmJson.modules)) {
          for (const m of cmJson.modules as Array<{
            id: string
            label: string
            localeCompleteness?: Record<Locale, LocaleCompletenessLevel>
          }>) {
            if (m.id && m.localeCompleteness) {
              cat[m.id] = { label: m.label, localeCompleteness: m.localeCompleteness }
            }
          }
        }
        setCommonModuleCatalog(cat)
      } else {
        setCommonModuleCatalog({})
      }

      setMissingKind(null)
      bumpPreviewReload()
    } catch (error) {
      console.error('Error fetching page data:', error)
      setPage(null)
      setCommonModuleCatalog({})
      setMissingKind('other')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPageData()
  }, [slug, router])

  const handleDeleteClick = (sectionId: string) => {
    setSectionToDelete(sectionId)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!sectionToDelete) return

    try {
      const response = await fetch(`/api/admin/sections/${sectionToDelete}/delete`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete section')
      }

      toastSuccess('Deleted')
      await fetchPageData()
      setSectionToDelete(null)
    } catch (error: any) {
      throw error // Let ConfirmDialog handle the error toast
    }
  }

  const handlePageDeleteConfirm = async () => {
    if (!slug || page?.deleteBlockedReason) return
    const response = await fetch(`/api/admin/pages/${encodeURIComponent(slug)}`, {
      method: 'DELETE',
      credentials: 'include',
    })
    const data = (await response.json().catch(() => ({}))) as { error?: string }
    if (!response.ok) {
      throw new Error(typeof data.error === 'string' ? data.error : 'Suppression impossible')
    }
    toastSuccess('Page supprimée')
    setPageDeleteDialogOpen(false)
    router.push('/admin/pages')
  }

  const handlePageCopyConfirm = async () => {
    if (!pageCopyDialog || !slug) return
    try {
      const res = await fetch(
        `/api/admin/pages/${encodeURIComponent(slug)}/copy-locale-content`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sourceLocale: defaultLocale,
            targetLocale: pageCopyDialog,
            writeAsDraft: true,
          }),
        },
      )
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Échec de la copie')
      }
      toastSuccess(
        `Copié en brouillon ${pageCopyDialog.toUpperCase()} (${data.sectionsCopied ?? 0} section(s)).`,
      )
      setPageCopyDialog(null)
      await fetchPageData()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    }
  }

  const handleMoveSection = async (sectionId: string, direction: 'up' | 'down') => {
    const currentIndex = sections.findIndex((s) => s.id === sectionId)
    if (currentIndex === -1) return

    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
    if (newIndex < 0 || newIndex >= sections.length) return

    const newOrder = [...sections]
    const [moved] = newOrder.splice(currentIndex, 1)
    newOrder.splice(newIndex, 0, moved)

    setIsProcessing(true)
    try {
      const response = await fetch(`/api/admin/pages/${slug}/sections/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          orderedSectionIds: newOrder.map((s) => s.id),
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to reorder sections')
      }

      toastSuccess('Order updated')
      await fetchPageData()
    } catch (error: any) {
      toastError(error.message || 'Failed to reorder sections')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleCheckPageLanguageScan = async () => {
    if (!slug) return
    const locLabel = editingLocale.toUpperCase()
    setCheckLangBusy(true)
    setCheckLangReport(null)
    setPageOpModal({
      title: `Vérifier la langue — ${locLabel}`,
      subtitle: slug,
      phase: 'running',
      steps: initialPageScanRunningSteps(locLabel),
      summaryLines: [],
    })
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => resolve())
    })
    try {
      const res = await fetch(
        `/api/admin/pages/${encodeURIComponent(slug)}/check-language/scan`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ targetLocale: editingLocale }),
        },
      )
      const payload = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(typeof payload.error === 'string' ? payload.error : 'Scan impossible')
      }
      setCheckLangReport({ ...payload, mode: 'scan' })
      const built = buildPageScanSuccessModal(payload, locLabel, slug)
      setPageOpModal({
        title: `Vérifier la langue — ${locLabel}`,
        subtitle: slug,
        phase: 'success',
        ...built,
      })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Scan impossible'
      setPageOpModal({
        title: `Vérifier la langue — ${locLabel}`,
        subtitle: slug,
        phase: 'error',
        steps: [
          {
            id: 'scan-fail',
            label: 'Analyse linguistique de la page',
            detail: msg,
            status: 'error',
          },
        ],
        summaryLines: [],
        errorMessage: msg,
      })
      toastError(msg)
    } finally {
      setCheckLangBusy(false)
    }
  }

  const handleCheckPageLanguageApply = async () => {
    if (!slug) return
    const locLabel = editingLocale.toUpperCase()
    if (
      !window.confirm(
        `Corriger automatiquement le brouillon ${locLabel} ?\n\n` +
          'Seuls les champs détectés comme mauvaise langue, mixtes ou en-têtes courts éligibles (allowlist sectionI18nPolicy) seront retraduits vers cette langue. ' +
          'Écriture DRAFT (SectionContent + PageI18n) uniquement — pas le PUBLISHED.\n\n' +
          'Les en-têtes courts déjà dans la bonne langue (ou ambigus sur la locale par défaut) sont ignorés et listés dans le résumé.',
      )
    ) {
      return
    }
    setCheckLangApplyBusy(true)
    setPageOpModal({
      title: `Corriger le brouillon — ${locLabel}`,
      subtitle: slug,
      phase: 'running',
      steps: initialPageApplyRunningSteps(locLabel),
      summaryLines: [],
    })
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => resolve())
    })
    try {
      const res = await fetch(
        `/api/admin/pages/${encodeURIComponent(slug)}/check-language/apply`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ targetLocale: editingLocale }),
        },
      )
      const payload = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          [payload.error, payload.detail].filter(Boolean).join(' — ') || 'Correction impossible',
        )
      }
      const built = buildPageApplySuccessModal(payload, locLabel, slug)
      setPageOpModal({
        title: `Corriger le brouillon — ${locLabel}`,
        subtitle: slug,
        phase: 'success',
        ...built,
      })
      setCheckLangReport({ ...payload, mode: 'afterApply' })
      await fetchPageData()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Correction impossible'
      setPageOpModal({
        title: `Corriger le brouillon — ${locLabel}`,
        subtitle: slug,
        phase: 'error',
        steps: [
          {
            id: 'apply-fail',
            label: 'Correction ou enregistrement du brouillon',
            detail: msg,
            status: 'error',
          },
        ],
        summaryLines: [],
        errorMessage: msg,
      })
      toastError(msg)
    } finally {
      setCheckLangApplyBusy(false)
    }
  }

  const handlePublishPage = async () => {
    if (!slug) return
    const locLabel = editingLocale.toUpperCase()
    if (
      !window.confirm(
        `Publier la page « ${slug} » en ${locLabel} ?\n\n` +
          'Toutes les sections de cette page qui ont un brouillon ' +
          `${locLabel} verront leur version publiée mise à jour ` +
          '(DRAFT → PUBLISHED). Les sections sans brouillon dans cette ' +
          'langue restent inchangées.\n\n' +
          'Le site public reflète immédiatement la nouvelle version.',
      )
    ) {
      return
    }
    setPublishBusy(true)
    setPageOpModal({
      title: `Publier la page — ${locLabel}`,
      subtitle: slug,
      phase: 'running',
      steps: initialPagePublishRunningSteps(locLabel),
      summaryLines: [],
    })
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => resolve())
    })
    try {
      const res = await fetch(
        `/api/admin/pages/${encodeURIComponent(slug)}/publish`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ targetLocale: editingLocale }),
        },
      )
      const payload = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          typeof payload.error === 'string' ? payload.error : 'Publication impossible',
        )
      }
      const built = buildPagePublishSuccessModal(payload, locLabel, slug)
      setPageOpModal({
        title: `Publier la page — ${locLabel}`,
        subtitle: slug,
        phase: 'success',
        ...built,
      })
      toastSuccess(
        `Page publiée en ${locLabel} — ${payload.publishedSectionsCount ?? 0} section(s).`,
      )
      await fetchPageData()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Publication impossible'
      setPageOpModal({
        title: `Publier la page — ${locLabel}`,
        subtitle: slug,
        phase: 'error',
        steps: [
          {
            id: 'publish-fail',
            label: 'Publication des sections',
            detail: msg,
            status: 'error',
          },
        ],
        summaryLines: [],
        errorMessage: msg,
      })
      toastError(msg)
    } finally {
      setPublishBusy(false)
    }
  }

  const checkLangRows = useMemo(
    () => (checkLangReport ? pageCheckReportToRows(checkLangReport, slug, editingLocale) : []),
    [checkLangReport, slug, editingLocale],
  )
  const checkLangAggregate = useMemo(
    () => (checkLangReport ? pageCheckReportAggregate(checkLangReport) : undefined),
    [checkLangReport],
  )

  const narrowSectionKey = useMemo(() => {
    if (!narrowSectionPreviewId) return null
    return sections.find((s) => s.id === narrowSectionPreviewId)?.key ?? null
  }, [narrowSectionPreviewId, sections])

  const narrowSectionForPreview = useMemo(() => {
    if (!narrowSectionPreviewId) return null
    return sections.find((s) => s.id === narrowSectionPreviewId) ?? null
  }, [narrowSectionPreviewId, sections])

  const narrowSectionDisplay = useMemo(() => {
    if (!narrowSectionForPreview) return null
    return formatAdminSectionDisplayLine(narrowSectionForPreview, commonModuleCatalog)
  }, [narrowSectionForPreview, commonModuleCatalog])

  const displayTitle = useMemo(() => {
    if (!page) return slug
    const row = page.pageI18n?.find((r) => r.locale === editingLocale)
    return (
      (row?.title?.trim() && row.title) ||
      (editingLocale === defaultLocale ? page.title?.trim() : '') ||
      slug
    )
  }, [page, editingLocale, slug])

  const localeMetadataInitial = useMemo((): PageLocaleMetadataInitial | null => {
    if (!page) return null
    const row = page.pageI18n?.find((r) => r.locale === editingLocale)
    return {
      title:
        row?.title ??
        (editingLocale === defaultLocale ? (page.title ?? '') : ''),
      description:
        row?.description ??
        (editingLocale === defaultLocale ? (page.description ?? '') : ''),
      navMegaCategory: row?.navMegaCategory ?? '',
      navMegaDescription: row?.navMegaDescription ?? '',
    }
  }, [page, editingLocale])

  const previewUrl = useMemo(() => {
    if (!slug) return ''
    const loc = encodeURIComponent(previewLocale)
    if (narrowSectionPreviewId) {
      return `/preview/section/${encodeURIComponent(narrowSectionPreviewId)}?locale=${loc}`
    }
    return `/preview/${encodeURIComponent(slug)}?locale=${loc}`
  }, [slug, previewLocale, narrowSectionPreviewId])

  const previewPanelTitle = useMemo(() => {
    if (narrowSectionPreviewId && narrowSectionDisplay) {
      return `Module · ${narrowSectionDisplay.line}`
    }
    return displayTitle
  }, [narrowSectionPreviewId, narrowSectionDisplay, displayTitle])

  const openSectionPreview = useCallback((sectionId: string) => {
    setNarrowSectionPreviewId(sectionId)
    setPreviewReloadEpoch((e) => e + 1)
  }, [])

  const previewLocaleLevels = useMemo(() => {
    if (!page) return undefined
    const { locales } = computePageLocaleCompleteness({
      id: page.id,
      template: page.template,
      title: page.title,
      description: page.description,
      pageI18n: page.pageI18n ?? [],
      sections: sections.map((s) => ({
        id: s.id,
        contents: s.contents.map((c) => ({ locale: c.locale, status: c.status })),
      })),
    })
    return locales
  }, [page, sections])

  const previewToolbar = useMemo(
    () => ({
      locale: previewLocale,
      onLocaleChange: setPreviewLocale,
      localeLevels: previewLocaleLevels,
      device: previewDevice,
      onDeviceChange: setPreviewDevice,
    }),
    [previewLocale, previewLocaleLevels, previewDevice],
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!page) {
    if (missingKind === 'article') {
      return (
        <div className="max-w-2xl">
          <Link href="/admin/pages" className="text-sm text-indigo-600 hover:text-indigo-800">
            ← Toutes les pages
          </Link>
          <h1 className="mt-4 text-2xl font-bold text-gray-900">Gabarit article — pas en base (sur cette BDD)</h1>
          <p className="mt-3 text-gray-600">
            L’URL <span className="font-mono text-sm">/admin/pages/article</span> est la bonne. L’API renvoie 404 :
            il n’y a pas de ligne <span className="font-mono">pages.slug = &apos;article&apos;</span> pour le{' '}
            <code className="rounded bg-gray-100 px-1">DATABASE_URL</code> de ce serveur, ou le schéma n’est pas à jour
            (migrations).
          </p>
          <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
            <p className="font-medium">Depuis le dossier web du dépôt (ex. clone sous ~/dev) :</p>
            <pre className="mt-2 overflow-x-auto rounded bg-white p-3 text-xs text-gray-800 shadow-inner">
              cd ~/dev/vancelian-app/services/arquantix/web{'\n'}
              npx prisma migrate deploy{'\n'}
              npx tsx scripts/init-article-template-page.ts
            </pre>
            <p className="mt-2 text-xs text-amber-900/90">
              Utilise le même <span className="font-mono">.env</span> que <span className="font-mono">npm run dev</span>
              . N’ouvre pas l’admin avec <span className="font-mono">/fr/admin/…</span> (redirigé vers{' '}
              <span className="font-mono">/admin/…</span>).
            </p>
          </div>
        </div>
      )
    }
    if (missingKind === 'exclusiveOfferGabarit') {
      return (
        <div className="max-w-2xl">
          <Link href="/admin/pages" className="text-sm text-indigo-600 hover:text-indigo-800">
            ← Toutes les pages
          </Link>
          <h1 className="mt-4 text-2xl font-bold text-gray-900">
            Gabarit offre exclusive — pas en base (sur cette BDD)
          </h1>
          <p className="mt-3 text-gray-600">
            L’URL <span className="font-mono text-sm">/admin/pages/exclusive-offer</span> est la bonne. L’API renvoie
            404 : il n’y a pas de ligne <span className="font-mono">pages.slug = &apos;exclusive-offer&apos;</span> pour
            le <code className="rounded bg-gray-100 px-1">DATABASE_URL</code> de ce serveur, ou le schéma n’est pas à
            jour (migrations).
          </p>
          <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
            <p className="font-medium">Depuis le dossier web du dépôt :</p>
            <pre className="mt-2 overflow-x-auto rounded bg-white p-3 text-xs text-gray-800 shadow-inner">
              cd ~/dev/vancelian-app/services/arquantix/web{'\n'}
              npx prisma migrate deploy{'\n'}
              npx tsx scripts/init-exclusive-offer-template-page.ts
            </pre>
            <p className="mt-2 text-xs text-amber-900/90">
              Utilise le même <span className="font-mono">.env</span> que <span className="font-mono">npm run dev</span>
              .
            </p>
          </div>
        </div>
      )
    }
    return (
      <div className="flex max-w-lg flex-col items-start gap-2">
        <Link href="/admin/pages" className="text-sm text-indigo-600 hover:text-indigo-800">
          ← Toutes les pages
        </Link>
        <div className="text-gray-700">Aucune page CMS avec ce slug, ou erreur de chargement.</div>
      </div>
    )
  }

  return (
    <>
      <PagePreviewDrawer
        open={previewDrawerOpen}
        title={previewPanelTitle}
        previewUrl={previewUrl}
        onClose={() => setPreviewDrawerOpen(false)}
        toolbar={previewToolbar}
        reloadEpoch={previewReloadEpoch}
      />

      <section className="lg:grid lg:grid-cols-2 lg:items-start lg:divide-x lg:divide-slate-200">
        <div className="flex min-w-0 flex-col pb-8 lg:min-h-0 lg:pr-4">
      <ConfirmDialog
        open={pageDeleteDialogOpen}
        onOpenChange={setPageDeleteDialogOpen}
        title="Supprimer cette page ?"
        description={
          `Vous allez supprimer définitivement la page « ${slug} » (${sections.length} module(s) sur cette page). ` +
          'Toutes les sections et leurs contenus (brouillons et versions publiées), les métadonnées i18n de la page, ' +
          'et toutes les entrées de menu (tous menus) qui pointaient vers cette page seront supprimées. ' +
          'Cette action est irréversible.'
        }
        confirmLabel="Supprimer définitivement"
        cancelLabel="Annuler"
        onConfirm={handlePageDeleteConfirm}
        destructive
      />

      <ConfirmDialog
        open={!!pageCopyDialog}
        onOpenChange={(open) => {
          if (!open) setPageCopyDialog(null)
        }}
        title="Copier le contenu vers une autre langue"
        description={
          pageCopyDialog
            ? `Copie brute ${defaultLocale.toUpperCase()} → ${pageCopyDialog.toUpperCase()} pour cette page (brouillons uniquement).`
            : ''
        }
        confirmLabel="Copier en brouillon"
        cancelLabel="Annuler"
        destructive={false}
        onConfirm={handlePageCopyConfirm}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-6">
        <div>
          <div className="flex flex-wrap items-center gap-2 gap-y-1">
            <h1 className="text-3xl font-bold text-gray-900">{displayTitle}</h1>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Langue éditoriale active : <strong>{editingLocale.toUpperCase()}</strong> — les liens vers les sections
            utilisent cette locale.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:shrink-0">
          <button
            type="button"
            onClick={() => setPreviewDrawerOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 lg:hidden"
          >
            <Eye className="h-4 w-4" aria-hidden />
            Aperçu brouillon
          </button>
          <button
            type="button"
            disabled={
              !!page.deleteBlockedReason || isProcessing || checkLangBusy || publishBusy
            }
            title={page.deleteBlockedReason ?? 'Supprimer définitivement cette page CMS'}
            onClick={() => setPageDeleteDialogOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-2 text-sm font-medium text-red-700 shadow-sm hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" aria-hidden />
            Supprimer la page
          </button>
        <Link
          href="/admin/pages"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to Pages
        </Link>
        </div>
      </div>

      <div className="mb-4 max-w-3xl space-y-3">
        <PageNavMegaIconCard
          slug={slug}
          initialNavMegaIconMediaId={page.navMegaIconMediaId ?? null}
          initialShowInMegaMenu={page.showInMegaMenu !== false}
          primaryNavLinkState={page.primaryNavLinkState}
          sectionsCount={sections.length}
          onSaved={fetchPageData}
        />
        <AdminEditingLocaleBar contextLabel="Page" />
        {localeMetadataInitial ? (
          <PageLocaleMetadataForm
            slug={slug}
            locale={editingLocale}
            initial={localeMetadataInitial}
            onSaved={fetchPageData}
          />
        ) : null}
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2">
          <span className="text-[11px] font-medium text-slate-600">Copie rapide (brouillons) :</span>
          {(['en', 'it'] as const).map((loc) => (
            <button
              key={loc}
              type="button"
              onClick={() => setPageCopyDialog(loc)}
              className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            >
              {defaultLocale.toUpperCase()} → {loc.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-2 rounded-lg border border-indigo-200 bg-indigo-50/60 px-3 py-2">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-indigo-900">
                <Languages className="h-3.5 w-3.5" aria-hidden />
                Vérification de langue (brouillon)
              </div>
              <p className="mt-0.5 text-[11px] leading-snug text-indigo-900/80">
                Détecte (via <code className="text-[10.5px]">franc</code>) les champs textuels qui
                ne sont pas dans la langue éditée et propose une retraduction ciblée
                (<code>WRONG_LANGUAGE</code> / <code>MIXED_LANGUAGE</code>). Périmètre :
                <code className="text-[10.5px]"> sectionI18nPolicy</code> + PageI18n. DRAFT
                uniquement, PUBLISHED inchangé.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleCheckPageLanguageScan}
              disabled={checkLangBusy || checkLangApplyBusy || publishBusy || isProcessing}
              className="inline-flex items-center gap-1.5 rounded-md border border-indigo-300 bg-white px-2.5 py-1 text-[11px] font-medium text-indigo-800 shadow-sm hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Languages className="h-3.5 w-3.5" aria-hidden />
              {checkLangBusy ? 'Scan…' : `Vérifier la langue (${editingLocale.toUpperCase()})`}
            </button>
            <button
              type="button"
              onClick={handleCheckPageLanguageApply}
              disabled={checkLangBusy || checkLangApplyBusy || publishBusy || isProcessing}
              className="inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-white px-2.5 py-1 text-[11px] font-medium text-amber-900 shadow-sm hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Wand2 className="h-3.5 w-3.5" aria-hidden />
              {checkLangApplyBusy
                ? 'Correction…'
                : `Corriger le brouillon (${editingLocale.toUpperCase()})`}
            </button>
          </div>
        </div>
        <div className="flex flex-col gap-2 rounded-lg border border-emerald-200 bg-emerald-50/60 px-3 py-2">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-900">
                <Rocket className="h-3.5 w-3.5" aria-hidden />
                Publication (DRAFT → PUBLISHED)
              </div>
              <p className="mt-0.5 text-[11px] leading-snug text-emerald-900/80">
                Le site public lit la version <strong>publiée</strong> de chaque section. « Save Draft »
                et « Corriger le brouillon » n'écrivent que dans le brouillon. Cliquez sur Publier pour
                propager le brouillon de la locale active vers la version publique de toutes les
                sections de cette page (les sections sans brouillon dans cette langue restent
                inchangées).
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handlePublishPage}
              disabled={publishBusy || checkLangBusy || checkLangApplyBusy || isProcessing}
              className="inline-flex items-center gap-1.5 rounded-md border border-emerald-400 bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Rocket className="h-3.5 w-3.5" aria-hidden />
              {publishBusy
                ? 'Publication…'
                : `Publier la page (${editingLocale.toUpperCase()})`}
            </button>
            <span className="text-[10.5px] text-emerald-900/70">
              Pour publier seulement une section :
              {' '}
              <strong>/admin/sections/[id]</strong> · bouton « Publish ».
            </span>
          </div>
        </div>
      </div>

      {/* Rapport « Vérifier la langue » — visible après le premier scan/apply réussi. */}
      {checkLangReport ? (
        <div className="my-6">
          <I18nFindingsTable
            layout="single-page"
            title={
              checkLangReport.mode === 'afterApply'
                ? `Rapport post-correction — Page (${editingLocale.toUpperCase()})`
                : `Dernier rapport — Langue de la page (${editingLocale.toUpperCase()})`
            }
            rows={checkLangRows}
            aggregate={checkLangAggregate}
          />
        </div>
      ) : null}

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Modules sur cette page</h2>
          <p className="mt-0.5 text-xs text-slate-600">
            Ordre d’affichage sur le site (haut → bas). Pastilles : version publiée (vert), brouillon seul (ambre),
            absent (rouge).
          </p>
        </div>
        {isProcessing ? (
          <Button disabled className="shrink-0">
            <Plus className="mr-2 h-4 w-4" />
            Ajouter un module
          </Button>
        ) : (
          <Button asChild className="shrink-0">
            <Link href={`/admin/pages/${encodeURIComponent(slug)}/add-module`}>
              <Plus className="mr-2 h-4 w-4" />
              Ajouter un module
            </Link>
          </Button>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Module
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Langues
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {sections.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-sm text-gray-500">
                  Aucun module sur cette page.
                </td>
              </tr>
            ) : (
              sections.map((section) => {
                const rawKey = section.key.trim()
                const sectionCanon = resolveCanonicalSectionKey(rawKey) ?? rawKey
                const refId = section.commonModuleRefId ?? null
                const sectionI18n =
                  sectionCanon === 'common_module_ref' && refId && commonModuleCatalog[refId]
                    ? commonModuleCatalog[refId].localeCompleteness
                    : computeSectionContentLocaleCompleteness(section)
                const { line: rowLabelOneLine, tooltip: rowTooltip } = formatAdminSectionDisplayLine(
                  section,
                  commonModuleCatalog,
                )

                return (
                  <tr key={section.id}>
                    <td className="max-w-[min(28rem,50vw)] px-4 py-3 align-top">
                      <div
                        className="truncate text-sm font-medium text-gray-900"
                        title={rowTooltip}
                      >
                        {rowLabelOneLine}
                      </div>
                      {sectionCanon === 'common_module_ref' && refId ? (
                        <div
                          className="mt-0.5 truncate font-mono text-[11px] text-slate-400"
                          title={refId}
                        >
                          {refId.slice(0, 8)}…
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <LocaleCompletenessStrip levels={sectionI18n} variant="inline" />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium">
                      <div className="flex flex-wrap items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => openSectionPreview(section.id)}
                          disabled={isProcessing}
                          className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 text-[11px] font-medium text-slate-700 shadow-sm hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-900 disabled:opacity-40"
                          title="Aperçu de ce module seul — langues via le panneau à droite"
                        >
                          <Eye className="h-3.5 w-3.5" aria-hidden />
                          Aperçu
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMoveSection(section.id, 'up')}
                          disabled={isProcessing || sections.findIndex((s) => s.id === section.id) === 0}
                          className="p-1 text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-30"
                          title="Monter"
                        >
                          <ArrowUp className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMoveSection(section.id, 'down')}
                          disabled={
                            isProcessing ||
                            sections.findIndex((s) => s.id === section.id) === sections.length - 1
                          }
                          className="p-1 text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-30"
                          title="Descendre"
                        >
                          <ArrowDown className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteClick(section.id)}
                          disabled={isProcessing}
                          className="p-1 text-gray-400 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
                          title="Supprimer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                        {sectionCanon !== 'common_module_ref' ? (
                          <Link
                            href={`/admin/sections/${section.id}?locale=${editingLocale}`}
                            className="px-2 py-1 text-indigo-600 hover:text-indigo-900"
                          >
                            Modifier
                          </Link>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={(open) => {
          setDeleteDialogOpen(open)
          if (!open) setSectionToDelete(null)
        }}
        title="Confirmer la suppression"
        description="Cette action supprime une section et sera irréversible si vous la validez. Êtes-vous sûr de vouloir continuer ?"
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        onConfirm={handleDeleteConfirm}
        destructive
      />

      {/* Modale bloquante de progression — Vérifier la langue / Corriger le brouillon */}
      <AdminOperationProgressModal
        open={pageOpModal != null}
        title={pageOpModal?.title ?? ''}
        subtitle={pageOpModal?.subtitle}
        phase={pageOpModal?.phase ?? 'running'}
        steps={pageOpModal?.steps ?? []}
        summaryLines={pageOpModal?.summaryLines ?? []}
        errorMessage={pageOpModal?.errorMessage}
        footerHint={pageOpModal?.footerHint}
        onClose={() => setPageOpModal(null)}
      />
        </div>

        <div className="hidden min-h-0 min-w-0 flex-col lg:sticky lg:top-2 lg:flex lg:h-[calc(100dvh-5rem)] lg:max-h-[calc(100dvh-5rem)]">
          {narrowSectionPreviewId ? (
            <div className="shrink-0 border-b border-sky-200 bg-sky-50/90 px-3 py-2">
              <p className="truncate text-[11px] text-sky-950" title={narrowSectionDisplay?.tooltip}>
                Aperçu isolé :{' '}
                <strong className="font-semibold">
                  {narrowSectionDisplay?.line ?? narrowSectionKey ?? narrowSectionPreviewId}
                </strong>
                {narrowSectionKey ? (
                  <span className="ml-1 font-mono text-[10px] font-normal text-sky-900/70">
                    ({narrowSectionKey})
                  </span>
                ) : null}
              </p>
              <button
                type="button"
                onClick={() => {
                  setNarrowSectionPreviewId(null)
                  setPreviewReloadEpoch((e) => e + 1)
                }}
                className="mt-1.5 text-left text-[11px] font-medium text-indigo-700 underline decoration-indigo-300 hover:text-indigo-900"
              >
                ← Aperçu de toute la page
              </button>
            </div>
          ) : null}
          <PagePreviewPanel
            title={previewPanelTitle}
            previewUrl={previewUrl}
            dismissible={false}
            toolbar={previewToolbar}
            reloadEpoch={previewReloadEpoch}
            className="min-h-0 flex-1"
          />
        </div>
      </section>
    </>
  )
}

