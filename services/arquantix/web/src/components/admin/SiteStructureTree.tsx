'use client'

/**
 * Structure du site — lots 5–6 : lisibilité, aperçu, i18n par page, copie prudente inter-locales.
 */

import { useState, useMemo, useEffect, useRef } from 'react'
import Link from 'next/link'
import type {
  SiteTreeGlobalCommonModuleRow,
  SiteTreeNavRightRailRow,
  SiteTreeNode,
} from '@/lib/cms/buildSiteTree'
import {
  EXCLUSIVE_OFFER_GABARIT_SLUG,
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
  VAULT_BUILDER_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'
import { defaultLocale, getLocaleOrDefault, supportedLocales, type Locale } from '@/config/locales'
import { siteStructureEditorHref } from '@/lib/admin/siteStructureEditorHref'
import { siteStructurePublicUrl } from '@/lib/admin/siteStructurePublicUrl'

/**
 * Origine du site public injectée au build via `NEXT_PUBLIC_SITE_URL`.
 * Utile quand l'admin tourne sur un sous-domaine séparé (ex.
 * `console.arquantix.com`) : on préfixe les URLs publiques pour que les
 * iframes / liens ciblent bien `https://arquantix.com/...` cross-host
 * (sinon 404 sur le sous-domaine console qui ne sert que `/admin*` et
 * `/preview/*`).
 *
 * En dev local sans variable définie : on retombe sur un path relatif,
 * l'admin et le site sont sur le même origin → fonctionnement inchangé.
 */
const PUBLIC_SITE_ORIGIN = (process.env.NEXT_PUBLIC_SITE_URL || '').replace(/\/$/, '')

function toPublicHref(path: string): string {
  if (!path) return path
  if (/^https?:\/\//i.test(path)) return path
  return PUBLIC_SITE_ORIGIN ? `${PUBLIC_SITE_ORIGIN}${path}` : path
}

function publicHrefForNode(node: SiteTreeNode, locale: string): string {
  return toPublicHref(siteStructurePublicUrl(node, locale))
}
import { analyzeSiteTreeStructure } from '@/lib/admin/siteStructureTreeMeta'
import { mustStayStructuralRoot } from '@/lib/admin/pageStructureValidation'
import {
  buildParentSelectOptions,
  findNodeById,
} from '@/lib/admin/siteStructureTreeEditing'
import {
  collectVisualSiblingsForReorder,
  isExclusiveOfferVaultPage,
  mergeSiblingOrderPreservingHidden,
} from '@/lib/admin/siteStructureReorder'
import type { LocaleCompletenessLevel } from '@/lib/admin/pageLocaleCompleteness'
import { LocaleCompletenessStrip } from '@/components/admin/LocaleCompletenessStrip'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { PagePreviewDrawer } from '@/components/admin/PagePreviewDrawer'
import { PagePreviewPanel } from '@/components/admin/PagePreviewPanel'
import { cn } from '@/lib/utils'
import { useAdminEditingLocale } from '@/components/admin/AdminEditingLocaleContext'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import {
  ChevronRight,
  ChevronDown,
  ExternalLink,
  Pencil,
  Package,
  Home,
  FolderKanban,
  FileText,
  RefreshCw,
  AlertTriangle,
  Info,
  ChevronUp,
  Layers,
  MoreHorizontal,
  Eye,
  Menu,
  Copy,
  Globe,
  Newspaper,
  MousePointerClick,
  Plus,
  PlusCircle,
  LayoutTemplate,
  Lock,
} from 'lucide-react'

/** Tous les ids de nœuds qui ont des enfants — état initial : replier l’arborescence. */
function collectNodeIdsWithChildren(nodes: SiteTreeNode[]): string[] {
  const ids: string[] = []
  const walk = (n: SiteTreeNode) => {
    if (n.children.length > 0) {
      ids.push(n.id)
      for (const c of n.children) walk(c)
    }
  }
  for (const n of nodes) walk(n)
  return ids
}

/** Sélecteur de langue dans la zone droite (même gabarit que les boutons d’action, flèches ↑↓). */
function LanguageSwitcherTreeRow({
  id,
  label,
  enabled,
  structureLocale,
  index,
  total,
  readOnly,
  reordering,
  onReorder,
}: {
  id: string
  label: string
  enabled: boolean
  structureLocale: Locale
  index: number
  total: number
  readOnly: boolean
  reordering: boolean
  onReorder: (itemId: string, direction: 'up' | 'down') => void
}) {
  const padLeft = 12
  const localesHint = supportedLocales.map((l) => l.toUpperCase()).join(' · ')

  return (
    <li className="list-none" aria-label={`Sélecteur de langue — ${label}`}>
      <div
        className="group flex flex-col gap-1 rounded-r-md border-b border-slate-100 border-l-[3px] border-l-emerald-500 bg-emerald-50/20 py-2 pr-2 transition-colors duration-200 hover:bg-emerald-50/35"
        style={{ paddingLeft: padLeft }}
        title={`Ordre identique au menu public (locale édition de ce panneau : ${structureLocale.toUpperCase()}).`}
      >
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <Globe className="h-4 w-4 shrink-0 text-emerald-800" aria-hidden />

          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-semibold text-slate-900">{label.trim() || 'Langue'}</span>
            <span
              className="max-w-[min(100%,280px)] truncate font-mono text-[11px] text-slate-500"
              title={`Locales proposées : ${localesHint}`}
            >
              {localesHint}
            </span>
            <span className="inline-flex rounded border border-emerald-200 bg-white px-1.5 py-0.5 font-mono text-[10px] font-semibold text-emerald-900">
              langue
            </span>
            {!enabled ? (
              <span className="inline-flex rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-amber-900">
                désactivé
              </span>
            ) : null}
          </div>

          <div className="flex shrink-0 items-center gap-0.5 border-l border-emerald-200/80 pl-2">
            <button
              type="button"
              disabled={readOnly || reordering || index <= 0}
              onClick={() => onReorder(id, 'up')}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-40"
              title="Monter (zone droite)"
              aria-label="Monter le sélecteur de langue"
            >
              <ChevronUp className="h-4 w-4" />
            </button>
            <button
              type="button"
              disabled={readOnly || reordering || index >= total - 1}
              onClick={() => onReorder(id, 'down')}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-40"
              title="Descendre (zone droite)"
              aria-label="Descendre le sélecteur de langue"
            >
              <ChevronDown className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </li>
  )
}

function StructureZone1Banner() {
  return (
    <li className="list-none" aria-label="Zone 1">
      <div
        className="rounded-r-md border border-slate-200/90 bg-gradient-to-r from-slate-100/90 to-white py-2.5 pr-2 pl-3 shadow-sm"
        style={{ paddingLeft: 12 }}
      >
        <span className="text-[11px] font-bold uppercase tracking-wide text-slate-800">
          Zone 1 — Pages & menu du site
        </span>
        <p className="mt-0.5 text-[10px] leading-snug text-slate-600">
          Arborescence des pages, alignement menu centre, puis zone droite (langue & boutons).
        </p>
      </div>
    </li>
  )
}

function MenuPagesZoneDivider({
  onAddPage,
  readOnlyStructure,
}: {
  onAddPage?: () => void
  readOnlyStructure?: boolean
}) {
  return (
    <li className="list-none" aria-label="Zone pages du menu">
      <div
        className="rounded-r-md border-b border-slate-100 border-l-[3px] border-l-slate-500 bg-slate-50/50 py-2 pr-2 pl-3"
        style={{ paddingLeft: 12 }}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
              Pages du menu (centre)
            </span>
            <p className="mt-0.5 text-[10px] leading-snug text-slate-500">
              Entrées liées aux pages CMS — ordre aligné sur le menu public.
            </p>
          </div>
          {onAddPage ? (
            <Button
              type="button"
              onClick={onAddPage}
              disabled={readOnlyStructure}
              className="h-8 shrink-0 gap-1.5 bg-slate-900 px-2.5 text-[11px] text-white hover:bg-slate-800 disabled:opacity-50"
            >
              <PlusCircle className="h-3.5 w-3.5" />
              Ajouter une page
            </Button>
          ) : null}
        </div>
      </div>
    </li>
  )
}

function NavActionsZoneHeader({
  onAddNavButton,
  readOnlyStructure,
}: {
  onAddNavButton?: () => void
  readOnlyStructure?: boolean
}) {
  return (
    <li className="list-none" aria-label="Zone droite du menu">
      <div
        className="rounded-r-md border-b border-slate-100 border-l-[3px] border-l-emerald-600 bg-emerald-50/40 py-2 pr-2 pl-3"
        style={{ paddingLeft: 12 }}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-emerald-950">
              Zone droite du menu
            </span>
            <p className="mt-0.5 text-[10px] leading-snug text-emerald-900/85">
              Sélecteur de langue et boutons d’action (Connexion, S’inscrire, etc.) — ordre unique, après les pages du
              menu.
            </p>
          </div>
          {onAddNavButton ? (
            <Button
              type="button"
              variant="outline"
              onClick={onAddNavButton}
              disabled={readOnlyStructure}
              className="h-8 shrink-0 gap-1.5 border-slate-300 bg-white px-2.5 text-[11px] text-slate-800 hover:bg-slate-50 disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" />
              Ajouter un bouton
            </Button>
          ) : null}
        </div>
      </div>
    </li>
  )
}

function GlobalModulesZoneHeader({
  onAddCommonModule,
  readOnlyStructure,
}: {
  onAddCommonModule?: () => void
  readOnlyStructure?: boolean
}) {
  return (
    <li className="list-none" aria-label="Zone modules communs">
      <div
        className="rounded-r-md border-b border-slate-100 border-l-[3px] border-l-sky-600 bg-sky-50/50 py-2 pr-2 pl-3"
        style={{ paddingLeft: 12 }}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-sky-950">
              Zone 2 — Modules communs
            </span>
            <p className="mt-0.5 text-[10px] leading-snug text-sky-900/85">
              Footer obligatoire ; autres modules (ex. CTA) optionnels — réutilisables via la section « Module commun
              (réutilisable) » sur une page.
            </p>
          </div>
          {onAddCommonModule && !readOnlyStructure ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 shrink-0 gap-1 border-sky-300 bg-white px-2.5 text-[11px] text-sky-950 hover:bg-sky-50"
              onClick={onAddCommonModule}
            >
              <Plus className="h-3.5 w-3.5" />
              Ajouter
            </Button>
          ) : null}
        </div>
      </div>
    </li>
  )
}

function GlobalCommonModuleTreeRow({
  row,
  locale,
  onOpenPreview,
}: {
  row: SiteTreeGlobalCommonModuleRow
  locale: Locale
  onOpenPreview: (row: SiteTreeGlobalCommonModuleRow, previewLocale: Locale) => void
}) {
  return (
    <li className="list-none" aria-label={`Module ${row.label}`}>
      <div
        className="group flex flex-col gap-1 rounded-r-md border-b border-slate-100 border-l-[3px] border-l-sky-500 bg-sky-50/15 py-2 pr-2 transition-colors duration-200 hover:bg-sky-50/30"
        style={{ paddingLeft: 12 }}
      >
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <LayoutTemplate className="h-4 w-4 shrink-0 text-sky-800" aria-hidden />

          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1">
            <span className="inline-flex min-w-0 max-w-full flex-wrap items-center gap-2">
              <span className="shrink-0 font-semibold text-slate-900">{row.label}</span>
              {row.systemLocked ? (
                <span className="inline-flex shrink-0 items-center gap-1 rounded border border-sky-200 bg-white px-1.5 py-0.5 font-mono text-[10px] font-semibold text-sky-900">
                  <Lock className="h-3 w-3" aria-hidden />
                  obligatoire
                </span>
              ) : null}
            </span>
            <span className="max-w-[min(100%,360px)] truncate text-[11px] text-slate-500" title={row.description}>
              {row.description}
            </span>
            <LocaleCompletenessStrip levels={row.localeCompleteness} variant="inline" />
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-1 border-l border-sky-200/80 pl-2">
            <Link
              href={row.editHref}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 text-[11px] font-medium text-slate-700 shadow-sm hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-900"
            >
              <Pencil className="h-3.5 w-3.5" />
              Éditer
            </Link>
            {!row.systemLocked ? (
              <>
                <button
                  type="button"
                  onClick={() => onOpenPreview(row, locale)}
                  className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 text-[11px] font-medium text-slate-700 shadow-sm hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-900"
                  title="Aperçu du module seul (sans quitter la page)"
                >
                  <Eye className="h-3.5 w-3.5" />
                  Aperçu
                </button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm hover:bg-slate-50"
                      aria-label="Aperçu par langue"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                      Aperçu du module
                    </DropdownMenuLabel>
                    {supportedLocales.map((loc) => (
                      <DropdownMenuItem
                        key={`cm-preview-${row.id}-${loc}`}
                        className="flex cursor-pointer items-center gap-2 text-xs"
                        onSelect={() => onOpenPreview(row, loc)}
                      >
                        <Eye className="h-3.5 w-3.5" />
                        Aperçu · {loc.toUpperCase()}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </li>
  )
}

function NavActionButtonTreeRow({
  row,
  index,
  total,
  readOnly,
  reordering,
  onReorder,
}: {
  row: Extract<SiteTreeNavRightRailRow, { kind: 'button' }>
  index: number
  total: number
  readOnly: boolean
  reordering: boolean
  onReorder: (id: string, direction: 'up' | 'down') => void
}) {
  const padLeft = 12
  const urlPreview = (row.externalUrl || '').trim() || '—'

  return (
    <li className="list-none" aria-label={`Bouton menu ${row.label}`}>
      <div
        className="group flex flex-col gap-1 rounded-r-md border-b border-slate-100 border-l-[3px] border-l-emerald-500 bg-emerald-50/20 py-2 pr-2 transition-colors duration-200 hover:bg-emerald-50/35"
        style={{ paddingLeft: padLeft }}
      >
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <MousePointerClick className="h-4 w-4 shrink-0 text-emerald-800" aria-hidden />

          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-semibold text-slate-900">{row.label}</span>
            <span
              className="max-w-[min(100%,320px)] truncate font-mono text-[11px] text-slate-500"
              title={urlPreview}
            >
              {urlPreview}
            </span>
            <LocaleCompletenessStrip levels={row.localeCompleteness} variant="inline" />
            <span className="inline-flex rounded border border-emerald-200 bg-white px-1.5 py-0.5 font-mono text-[10px] font-semibold text-emerald-900">
              {(row.buttonStyle || 'primary').toLowerCase()}
            </span>
            {!row.enabled ? (
              <span className="inline-flex rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-amber-900">
                désactivé
              </span>
            ) : null}
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-1 border-l border-emerald-200/80 pl-2">
            <Link
              href={`/admin/pages/nav-action/${encodeURIComponent(row.id)}`}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 text-[11px] font-medium text-slate-700 shadow-sm hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-900"
            >
              <Pencil className="h-3.5 w-3.5" />
              Éditer
            </Link>
            <button
              type="button"
              disabled={readOnly || reordering || index <= 0}
              onClick={() => onReorder(row.id, 'up')}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-40"
              title="Monter (parmi les boutons à droite)"
              aria-label="Monter le bouton"
            >
              <ChevronUp className="h-4 w-4" />
            </button>
            <button
              type="button"
              disabled={readOnly || reordering || index >= total - 1}
              onClick={() => onReorder(row.id, 'down')}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-40"
              title="Descendre (parmi les boutons à droite)"
              aria-label="Descendre le bouton"
            >
              <ChevronDown className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </li>
  )
}

function NodeIcon({ node }: { node: SiteTreeNode }) {
  if (node.isVirtual && node.articleId) {
    return <Newspaper className="h-4 w-4 shrink-0 text-cyan-800" aria-hidden />
  }
  if (node.pageRole === 'HOME' || node.slug === 'home') {
    return <Home className="h-4 w-4 shrink-0 text-violet-700" aria-hidden />
  }
  if (isArticleCmsGabarit(node)) {
    return <Layers className="h-4 w-4 shrink-0 text-amber-800" aria-hidden />
  }
  if (isExclusiveOfferCmsGabarit(node)) {
    return <Layers className="h-4 w-4 shrink-0 text-rose-800" aria-hidden />
  }
  if (node.pageRole === 'PROJECTS_HUB' || node.slug === 'projects') {
    return <FolderKanban className="h-4 w-4 shrink-0 text-sky-800" aria-hidden />
  }
  if (node.template === VAULT_BUILDER_TEMPLATE) {
    return <Package className="h-4 w-4 shrink-0 text-amber-800" aria-hidden />
  }
  return <FileText className="h-4 w-4 shrink-0 text-slate-600" aria-hidden />
}

function isArticleCmsGabarit(node: SiteTreeNode): boolean {
  return node.slug === 'article' && node.template === 'article'
}

function isExclusiveOfferCmsGabarit(node: SiteTreeNode): boolean {
  return node.slug === EXCLUSIVE_OFFER_GABARIT_SLUG && node.template === EXCLUSIVE_OFFER_GABARIT_TEMPLATE
}

function rowTypeBackground(node: SiteTreeNode): string {
  if (node.isVirtual && node.articleId) return 'bg-cyan-50/25'
  if (isArticleCmsGabarit(node)) return 'bg-amber-50/40'
  if (isExclusiveOfferCmsGabarit(node)) return 'bg-rose-50/35'
  if (node.pageRole === 'HOME' || node.slug === 'home') return 'bg-violet-50/40'
  if (node.pageRole === 'PROJECTS_HUB' || node.slug === 'projects') return 'bg-sky-50/35'
  if (node.template === VAULT_BUILDER_TEMPLATE) return 'bg-amber-50/35'
  return ''
}

function TreeRow({
  node,
  depth,
  locale,
  collapsedIds,
  toggleCollapsed,
  editMode,
  selectedId,
  onPickForStructure,
  onReorderRow,
  reordering,
  flashId,
  onOpenPreview,
  onNavigateToMenus,
  onCopyDraftFromDefault,
}: {
  node: SiteTreeNode
  depth: number
  locale: Locale
  collapsedIds: Set<string>
  toggleCollapsed: (id: string) => void
  editMode: boolean
  selectedId: string | null
  onPickForStructure: (node: SiteTreeNode) => void
  onReorderRow?: (node: SiteTreeNode, direction: 'up' | 'down') => void
  reordering?: boolean
  flashId: string | null
  onOpenPreview: (node: SiteTreeNode, previewLocale: Locale) => void
  onNavigateToMenus?: () => void
  onCopyDraftFromDefault: (slug: string, target: Locale) => void
}) {
  const hasChildren = node.children.length > 0
  const collapsed = collapsedIds.has(node.id)
  const publicHref = publicHrefForNode(node, locale)
  const isVault = node.template === VAULT_BUILDER_TEMPLATE
  const vaultAdminHref = `/admin/vault-builder?slug=${encodeURIComponent(node.slug)}${node.packagedProduct?.productType === 'EXCLUSIVE_OFFER' ? '&eo=1' : ''}`
  const isVirtualArticle = Boolean(node.isVirtual && node.articleId)
  const structureRootLocked = mustStayStructuralRoot(node)
  const showReorderControls = Boolean(
    editMode &&
      !isVirtualArticle &&
      !structureRootLocked &&
      !isExclusiveOfferVaultPage(node) &&
      onReorderRow,
  )
  const isSelected = selectedId === node.id
  const isFlashing = flashId === node.id
  const navBorder = node.showInNav
    ? 'border-l-[3px] border-l-emerald-500'
    : 'border-l-[3px] border-l-slate-200'

  const padLeft = 12 + depth * 18

  return (
    <li className="list-none">
      <div
        className={`group flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-slate-100 py-2 pr-2 transition-colors duration-200 hover:bg-slate-50/90 ${rowTypeBackground(node)} ${navBorder} ${isSelected ? 'bg-indigo-50/70' : ''} ${isFlashing ? 'ring-2 ring-emerald-400/90 ring-inset motion-safe:animate-[pulse_1.2s_ease-in-out_1]' : ''} rounded-r-md`}
        style={{ paddingLeft: padLeft }}
      >
        <div className="flex min-w-0 flex-1 items-center gap-2">
          {hasChildren ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                toggleCollapsed(node.id)
              }}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
              aria-expanded={!collapsed}
              aria-label={collapsed ? 'Déplier' : 'Replier'}
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          ) : (
            <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-current" />
            </span>
          )}

          <NodeIcon node={node} />

          <div
            role={editMode && !isVirtualArticle ? 'button' : undefined}
            tabIndex={editMode && !isVirtualArticle ? 0 : undefined}
            onClick={() => {
              if (editMode && !isVirtualArticle) onPickForStructure(node)
            }}
            onKeyDown={(e) => {
              if (!editMode || isVirtualArticle) return
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onPickForStructure(node)
              }
            }}
            title={
              editMode && !isVirtualArticle
                ? 'Cliquer pour modifier le parent (panneau ci-dessus)'
                : undefined
            }
            className={cn(
              'flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1 rounded-md outline-none',
              editMode &&
                !isVirtualArticle &&
                'cursor-pointer hover:bg-slate-100/90 -mx-1 px-1 py-0.5 focus-visible:ring-2 focus-visible:ring-indigo-400',
            )}
          >
            <span className="shrink-0 font-semibold text-slate-900">
              {node.title?.trim() || node.slug}
            </span>
            <span className="font-mono text-[11px] text-slate-500" title="Segment d’URL (sans préfixe de locale)">
              {node.slug.replace(/^\/+|\/+$/g, '') || '—'}
            </span>
            <LocaleCompletenessStrip levels={node.localeCompleteness} variant="inline" />
            {node.menuNavLink ? (
              <>
                <span
                  className="text-[10px] font-semibold uppercase tracking-wide text-slate-400"
                  title="Libellé affiché dans la barre de navigation (niveau 1)"
                >
                  menu
                </span>
                <LocaleCompletenessStrip levels={node.menuNavLink.labelCompleteness} variant="inline" />
              </>
            ) : null}
          </div>
        </div>

        {showReorderControls && (
          <div className="flex shrink-0 items-center gap-0.5 border-l border-slate-200/90 pl-2">
            <button
              type="button"
              disabled={reordering}
              onClick={(e) => {
                e.stopPropagation()
                onReorderRow!(node, 'up')
              }}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-40"
              title="Monter (même niveau que les pages voisines)"
              aria-label="Monter"
            >
              <ChevronUp className="h-4 w-4" />
            </button>
            <button
              type="button"
              disabled={reordering}
              onClick={(e) => {
                e.stopPropagation()
                onReorderRow!(node, 'down')
              }}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-40"
              title="Descendre (même niveau que les pages voisines)"
              aria-label="Descendre"
            >
              <ChevronDown className="h-4 w-4" />
            </button>
          </div>
        )}

        <div className="flex shrink-0 items-center gap-1 opacity-95 transition group-hover:opacity-100">
          {node.menuNavLink && !isVirtualArticle ? (
            <Link
              href={`/admin/pages/nav-menu-link/${encodeURIComponent(node.menuNavLink.menuItemId)}`}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 text-[11px] font-medium text-slate-700 shadow-sm hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-900"
            >
              <Pencil className="h-3.5 w-3.5" />
              Éditer
            </Link>
          ) : null}
          <button
            type="button"
            onClick={() => onOpenPreview(node, locale)}
            className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 text-[11px] font-medium text-slate-700 shadow-sm hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-900"
            title="Aperçu sans quitter la page"
          >
            <Eye className="h-3.5 w-3.5" />
            Aperçu
          </button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm hover:bg-slate-50"
                aria-label="Actions"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                Aperçu public
              </DropdownMenuLabel>
              {supportedLocales.map((loc) => (
                <DropdownMenuItem
                  key={`pv-${loc}`}
                  className="flex cursor-pointer items-center gap-2 text-xs"
                  onSelect={() => onOpenPreview(node, loc)}
                >
                  <Eye className="h-3.5 w-3.5" />
                  Aperçu · {loc.toUpperCase()}
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              {!isVirtualArticle && (
                <>
                  <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    Page CMS
                  </DropdownMenuLabel>
                  {supportedLocales.map((loc) => (
                    <DropdownMenuItem key={`ed-${loc}`} asChild>
                      <Link
                        href={`/admin/pages/${node.slug}?editingLocale=${loc}`}
                        className="flex cursor-pointer items-center gap-2 text-xs"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Éditer · {loc.toUpperCase()}
                      </Link>
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuSeparator />
                  <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    Copie (brouillons)
                  </DropdownMenuLabel>
                  <p className="px-2 pb-1 text-[10px] leading-snug text-slate-500">
                    Copie brute depuis {defaultLocale.toUpperCase()} vers la cible — relecture requise, sans
                    traduction auto.
                  </p>
                  {supportedLocales
                    .filter((l) => l !== defaultLocale)
                    .map((target) => (
                      <DropdownMenuItem
                        key={`cp-${target}`}
                        className="flex cursor-pointer items-center gap-2 text-xs"
                        onSelect={() => onCopyDraftFromDefault(node.slug, target)}
                      >
                        <Copy className="h-3.5 w-3.5" />
                        {defaultLocale.toUpperCase()} → {target.toUpperCase()}
                      </DropdownMenuItem>
                    ))}
                  <DropdownMenuSeparator />
                </>
              )}
              {isVirtualArticle && node.articleId && (
                <>
                  <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    Article blog
                  </DropdownMenuLabel>
                  <DropdownMenuItem asChild>
                    <Link
                      href={`/admin/articles/${node.articleId}`}
                      className="flex cursor-pointer items-center gap-2 text-xs"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      Ouvrir l’éditeur
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}
              <DropdownMenuItem asChild>
                <a
                  href={publicHref}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex cursor-pointer items-center gap-2"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  Onglet · locale éditée ({locale.toUpperCase()})
                </a>
              </DropdownMenuItem>
              {isVault && (
                <DropdownMenuItem asChild>
                  <Link href={vaultAdminHref} className="flex cursor-pointer items-center gap-2">
                    <Package className="h-3.5 w-3.5" />
                    Vault Builder
                  </Link>
                </DropdownMenuItem>
              )}
              {onNavigateToMenus && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="flex cursor-pointer items-center gap-2"
                    onSelect={() => onNavigateToMenus()}
                  >
                    <Menu className="h-3.5 w-3.5" />
                    Menu & alignement
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {hasChildren && !collapsed && (
        <ul className="relative ml-2 border-l border-slate-200/80 pl-1" style={{ marginLeft: padLeft + 6 }}>
          {node.children.map((child) => (
            <TreeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              locale={locale}
              collapsedIds={collapsedIds}
              toggleCollapsed={toggleCollapsed}
              editMode={editMode}
              selectedId={selectedId}
              onPickForStructure={onPickForStructure}
              onReorderRow={onReorderRow}
              reordering={reordering}
              flashId={flashId}
              onOpenPreview={onOpenPreview}
              onNavigateToMenus={onNavigateToMenus}
              onCopyDraftFromDefault={onCopyDraftFromDefault}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

export type SiteStructureTreeProps = {
  tree: SiteTreeNode[] | null
  loading: boolean
  error: string | null
  onRefresh: () => void | Promise<void>
  /** @deprecated La locale éditoriale vient du contexte admin (sélecteur global). */
  locale?: Locale
  /** Bascule vers l’onglet Menus (alignement) depuis le menu contextuel. */
  onNavigateToMenus?: () => void
  /** Ouvre le flux de création de page (modal côté parent). */
  onAddPage?: () => void
  /** Ouvre l’ajout d’un bouton menu (Connexion / Inscription, etc.) — modal côté parent. */
  onAddNavButton?: () => void
  /** Zone droite : langue + boutons d’action, ordre du menu primaire. */
  navRightRail?: SiteTreeNavRightRailRow[]
  /** Zone 2 : modules globaux (footer, …) — sans réordonnancement. */
  globalCommonModules?: SiteTreeGlobalCommonModuleRow[]
  /** Ouvre le dialogue de création d’un module commun (CTA, etc.). */
  onAddCommonModule?: () => void
  /** Désactive réorganisation des boutons (structure verrouillée). */
  readOnlyStructure?: boolean
  /** Incrémenté côté parent pour recharger l’iframe d’aperçu. */
  previewReloadEpoch?: number
  /** Une fois l’arbre chargé, ouvre l’aperçu sur la première page (ordre d’affichage racine). */
  autoOpenFirstPreviewOnLoad?: boolean
}

export function SiteStructureTree({
  tree,
  loading,
  error,
  onRefresh,
  locale: localeProp,
  onNavigateToMenus,
  onAddPage,
  onAddNavButton,
  navRightRail = [],
  globalCommonModules = [],
  onAddCommonModule,
  readOnlyStructure = false,
  previewReloadEpoch = 0,
  autoOpenFirstPreviewOnLoad = false,
}: SiteStructureTreeProps) {
  const { locale: localeFromCtx } = useAdminEditingLocale()
  const locale = getLocaleOrDefault(localeProp ?? localeFromCtx)
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(() => new Set())
  const [editMode, setEditMode] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [draftParentId, setDraftParentId] = useState<string>('')
  const [draftSortOrder, setDraftSortOrder] = useState<number>(0)
  const [saving, setSaving] = useState(false)
  const [reordering, setReordering] = useState(false)
  const [reorderingNavActions, setReorderingNavActions] = useState(false)
  const [panelError, setPanelError] = useState<string | null>(null)
  const [flashId, setFlashId] = useState<string | null>(null)
  const [previewNode, setPreviewNode] = useState<SiteTreeNode | null>(null)
  const [previewCommonModuleRow, setPreviewCommonModuleRow] =
    useState<SiteTreeGlobalCommonModuleRow | null>(null)
  const [previewLocale, setPreviewLocale] = useState<Locale>(locale)
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'mobile'>('desktop')
  const [copyDialog, setCopyDialog] = useState<{ slug: string; target: Locale } | null>(null)
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const autoFirstPreviewFiredRef = useRef(false)
  /** Un seul pliage initial par chargement d’arbre ; réinitialisé si `tree` repasse à null (erreur API). */
  const initialTreeCollapseAppliedRef = useRef(false)

  const triggerFlash = (id: string) => {
    if (flashTimer.current) clearTimeout(flashTimer.current)
    setFlashId(id)
    flashTimer.current = setTimeout(() => setFlashId(null), 2200)
  }

  useEffect(() => {
    return () => {
      if (flashTimer.current) clearTimeout(flashTimer.current)
    }
  }, [])

  useEffect(() => {
    if (tree == null) {
      initialTreeCollapseAppliedRef.current = false
      return
    }
    if (!tree.length) return
    if (initialTreeCollapseAppliedRef.current) return
    initialTreeCollapseAppliedRef.current = true
    setCollapsedIds(new Set(collectNodeIdsWithChildren(tree)))
  }, [tree])

  /**
   * Voir `toPublicHref` plus haut : préfixe l'URL publique avec
   * `NEXT_PUBLIC_SITE_URL` quand l'admin est servi sur un sous-domaine
   * séparé du site public (sinon l'iframe charge `console.arquantix.com/<path>`
   * qui est 404). Les URLs `/preview/*` restent relatives — elles sont
   * servies à la fois sur console et sur le site public.
   */
  const previewUrl = useMemo(() => {
    if (previewCommonModuleRow) {
      const loc = getLocaleOrDefault(previewLocale)
      return `/preview/common-module/${encodeURIComponent(previewCommonModuleRow.id)}?locale=${encodeURIComponent(loc)}`
    }
    if (previewNode) {
      return publicHrefForNode(previewNode, previewLocale)
    }
    return ''
  }, [previewCommonModuleRow, previewNode, previewLocale])

  const previewTitle = useMemo(() => {
    if (previewCommonModuleRow) return previewCommonModuleRow.label
    if (previewNode) return previewNode.title?.trim() || previewNode.slug
    return ''
  }, [previewCommonModuleRow, previewNode])

  const openStructurePreview = (node: SiteTreeNode, loc: Locale) => {
    setPreviewCommonModuleRow(null)
    setPreviewNode(node)
    setPreviewLocale(loc)
    setPreviewDevice('desktop')
  }

  const openCommonModulePreview = (row: SiteTreeGlobalCommonModuleRow, loc: Locale) => {
    setPreviewNode(null)
    setPreviewCommonModuleRow(row)
    setPreviewLocale(loc)
    setPreviewDevice('desktop')
  }

  const closeStructurePreview = () => {
    setPreviewNode(null)
    setPreviewCommonModuleRow(null)
    setPreviewDevice('desktop')
  }

  useEffect(() => {
    if (!autoOpenFirstPreviewOnLoad) return
    if (loading || error || !tree?.length || autoFirstPreviewFiredRef.current) return
    const first = tree[0]
    if (!first) return
    autoFirstPreviewFiredRef.current = true
    setPreviewNode(first)
    setPreviewLocale(locale)
    setPreviewDevice('desktop')
  }, [autoOpenFirstPreviewOnLoad, loading, error, tree, locale])

  const previewEditHref = useMemo(
    () => (previewNode ? siteStructureEditorHref(previewNode, previewLocale) : null),
    [previewNode, previewLocale],
  )

  const previewToolbar =
    previewCommonModuleRow != null
      ? {
          locale: previewLocale,
          onLocaleChange: setPreviewLocale,
          localeLevels: previewCommonModuleRow.localeCompleteness,
          device: previewDevice,
          onDeviceChange: setPreviewDevice,
          editPageHref: previewCommonModuleRow.editHref,
        }
      : previewNode != null
        ? {
            locale: previewLocale,
            onLocaleChange: setPreviewLocale,
            localeLevels: previewNode.localeCompleteness,
            device: previewDevice,
            onDeviceChange: setPreviewDevice,
            editPageHref: previewEditHref,
          }
        : undefined

  const previewOpen = previewNode != null || previewCommonModuleRow != null

  const toggleCollapsed = (id: string) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const meta = useMemo(() => (tree?.length ? analyzeSiteTreeStructure(tree) : null), [tree])

  const selectedNode = useMemo(() => {
    if (!tree || !selectedId) return null
    return findNodeById(tree, selectedId)
  }, [tree, selectedId])

  const parentOptions = useMemo(() => {
    if (!tree || !selectedNode) return []
    return buildParentSelectOptions(tree, selectedNode)
  }, [tree, selectedNode])

  const rootLocked = useMemo(
    () => (selectedNode ? mustStayStructuralRoot(selectedNode) : false),
    [selectedNode],
  )

  useEffect(() => {
    if (!selectedNode) return
    setDraftParentId(selectedNode.parentId ?? '')
    setDraftSortOrder(selectedNode.sortOrder)
    setPanelError(null)
  }, [selectedNode?.id, selectedNode?.parentId, selectedNode?.sortOrder])

  useEffect(() => {
    if (!tree?.length || !selectedId) return
    if (!findNodeById(tree, selectedId)) {
      setSelectedId(null)
    }
  }, [tree, selectedId])

  const onPickForStructure = (node: SiteTreeNode) => {
    setSelectedId(node.id)
    setPanelError(null)
  }

  const handleCopyConfirm = async () => {
    if (!copyDialog) return
    try {
      const res = await fetch(
        `/api/admin/pages/${encodeURIComponent(copyDialog.slug)}/copy-locale-content`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sourceLocale: defaultLocale,
            targetLocale: copyDialog.target,
            writeAsDraft: true,
          }),
        },
      )
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Échec de la copie')
      }
      toastSuccess(
        `${data.sectionsCopied ?? 0} section(s) copiée(s) en brouillon ${copyDialog.target.toUpperCase()}.`,
      )
      setCopyDialog(null)
      await onRefresh()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    }
  }

  const handleReorderNavAction = async (itemId: string, direction: 'up' | 'down') => {
    if (readOnlyStructure || !editMode) return
    setReorderingNavActions(true)
    setPanelError(null)
    try {
      const res = await fetch('/api/admin/menus/primary/items/reorder-nav-actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ itemId, direction }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.error || 'Échec du réordonnancement')
      }
      toastSuccess('Ordre de la zone droite (langue + boutons) mis à jour')
      await onRefresh()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Erreur'
      setPanelError(msg)
      toastError(msg)
    } finally {
      setReorderingNavActions(false)
    }
  }

  const handleSaveStructure = async () => {
    if (!selectedNode) return
    setSaving(true)
    setPanelError(null)
    const slug = selectedNode.slug
    const id = selectedNode.id
    try {
      const parentPayload = rootLocked ? undefined : draftParentId === '' ? null : draftParentId
      const sortPayload = draftSortOrder
      const res = await fetch(`/api/admin/pages/${encodeURIComponent(slug)}/structure`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...(rootLocked ? {} : { parentId: parentPayload }),
          sortOrder: sortPayload,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || data.message || 'Échec enregistrement')
      }
      toastSuccess('Structure enregistrée')
      triggerFlash(id)
      await onRefresh()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Erreur'
      setPanelError(msg)
      toastError(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleReorderNode = async (node: SiteTreeNode, direction: 'up' | 'down') => {
    if (!tree?.length) return
    setReordering(true)
    setPanelError(null)
    const id = node.id
    try {
      const vis = collectVisualSiblingsForReorder(tree, node)
      const visSlugs = vis.map((n) => n.slug)
      const idx = visSlugs.indexOf(node.slug)
      const j = direction === 'up' ? idx - 1 : idx + 1
      if (idx < 0 || j < 0 || j >= visSlugs.length) {
        toastError('Impossible de déplacer : déjà en tête ou en queue à ce niveau')
        return
      }
      const visNew = [...visSlugs]
      const tmp = visNew[idx]!
      visNew[idx] = visNew[j]!
      visNew[j] = tmp

      const ctxRes = await fetch(`/api/admin/pages/${encodeURIComponent(node.slug)}/structure`)
      const ctxData = await ctxRes.json().catch(() => ({}))
      if (!ctxRes.ok) {
        throw new Error(ctxData.error || ctxData.message || 'Échec lecture fratrie')
      }
      const fullDb: string[] = Array.isArray(ctxData.slugs) ? ctxData.slugs : []
      if (fullDb.length === 0) {
        throw new Error('Fratrie introuvable')
      }
      const visSlotSlugs = new Set(visSlugs)
      const slotCount = fullDb.filter((s) => visSlotSlugs.has(s)).length
      if (slotCount !== visNew.length) {
        throw new Error(
          'L’arborescence affichée ne correspond plus à la base — actualisez, puis réessayez.',
        )
      }
      const merged = mergeSiblingOrderPreservingHidden(fullDb, visNew, visSlotSlugs)

      const res = await fetch(`/api/admin/pages/${encodeURIComponent(node.slug)}/structure`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ siblingSlugsInOrder: merged }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.error || data.message || 'Échec')
      }
      toastSuccess('Ordre mis à jour')
      triggerFlash(id)
      await onRefresh()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Erreur'
      setPanelError(msg)
      toastError(msg)
    } finally {
      setReordering(false)
    }
  }

  return (
    <>
      <PagePreviewDrawer
        open={previewOpen}
        title={previewTitle}
        previewUrl={previewUrl}
        toolbar={previewToolbar}
        onClose={closeStructurePreview}
        reloadEpoch={previewReloadEpoch}
      />

      <ConfirmDialog
        open={!!copyDialog}
        onOpenChange={(open) => {
          if (!open) setCopyDialog(null)
        }}
        title="Copier le contenu vers une autre langue"
        description={
          copyDialog
            ? `Copie depuis ${defaultLocale.toUpperCase()} vers ${copyDialog.target.toUpperCase()} pour « ${copyDialog.slug} » : les sections cibles sont mises en DRAFT (les publiés ne sont pas écrasés). Les titres SEO PageI18n sont alignés quand possible.`
            : ''
        }
        confirmLabel="Copier en brouillon"
        cancelLabel="Annuler"
        destructive={false}
        onConfirm={handleCopyConfirm}
      />

    <section
      className={cn(
        'rounded-xl border border-slate-200/90 bg-white shadow-sm transition-shadow hover:shadow-md',
        previewOpen
          ? 'overflow-hidden lg:grid lg:h-[calc(100vh-10rem)] lg:min-h-[420px] lg:grid-cols-2 lg:divide-x lg:divide-slate-200'
          : 'overflow-hidden',
      )}
    >
      <div
        className={cn(
          'flex min-w-0 flex-col',
          previewOpen && 'lg:h-full lg:min-h-0 lg:overflow-y-auto',
        )}
      >
      <header className="border-b border-slate-100 bg-gradient-to-r from-slate-50/95 to-white px-4 py-3.5">
        <h2 className="text-base font-semibold tracking-tight text-slate-900">Structure du site</h2>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setEditMode((v) => !v)
              if (editMode) {
                setSelectedId(null)
                setPanelError(null)
              }
            }}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium shadow-sm transition ${
              editMode
                ? 'border-indigo-400 bg-indigo-100 text-indigo-950'
                : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            {editMode ? 'Terminer' : 'Réordonner les éléments'}
          </button>
          <button
            type="button"
            onClick={() => void onRefresh()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
        </div>
        <div className="mt-2 max-w-4xl space-y-2 text-xs leading-relaxed text-slate-600">
          <p>
            <strong>Menu du site :</strong> les pages sans parent (premier niveau de l’arborescence) correspondent en
            pratique aux entrées du menu primaire affiché sur le site public. L’ordre des lignes à ce niveau reprend
            l’ordre du menu primaire : c’est la source de vérité pour l’ordre d’apparition des liens dans la navigation
            (les réglages détaillés des entrées se font dans l’onglet Menus).
          </p>
          <p>
            Info : offres exclusives (vaults) regroupées sous le gabarit « exclusive-offer », et articles blog sous le
            gabarit « article ».
          </p>
          <p>
            Les gabarits servent à définir la mise en page de référence d’une page d’article ou d’un projet. Certains
            éléments sont des modules de type « tronc commun », d’autres sont liés au contenu proprement dit. Le
            contenu, quant à lui, est géré dans un autre espace CMS dédié (rédaction d’articles, Vault Builder / offres
            exclusives, etc.).
          </p>
        </div>
      </header>

      {editMode && (
        <div className="border-b border-indigo-100 bg-indigo-50/50 px-4 py-3 text-xs text-indigo-950">
          <p className="font-medium">Réorganiser le menu</p>
          <p className="mt-1 text-indigo-900/85">
            <strong>Pages (centre) :</strong> utilisez <strong>↑ ↓</strong> sur une ligne pour l’ordre au même niveau.{' '}
            <strong>Cliquez le titre</strong> d’une page pour choisir son <strong>parent</strong>, puis enregistrez.
            Les pages accueil / hub projets ne peuvent pas être déplacées ainsi.
          </p>
          <p className="mt-2 text-indigo-900/85">
            <strong>Zone droite (langue, Connexion, etc.) :</strong> les mêmes <strong>↑ ↓</strong> sur chaque ligne
            modifient l’ordre dans le menu public (sans changer l’ordre des pages du centre).
          </p>
          <p className="mt-2 text-indigo-900/85">
            <strong>Zone 2 — Modules communs :</strong> pas de flèches d’ordre ; ouvrez <strong>Éditer</strong> pour le
            pied de page ou un module réutilisable. Pour retirer un module optionnel, utilisez{' '}
            <strong>Supprimer le module</strong> en bas de sa page d’édition (évite les clics accidentels ici).
          </p>
        </div>
      )}

      {editMode && selectedNode && (
        <div className="border-b border-slate-200 bg-white px-4 py-4 transition-colors duration-300">
          <h3 className="text-sm font-semibold text-slate-900">
            Parent de « {selectedNode.title?.trim() || selectedNode.slug} »
          </h3>
          {panelError && (
            <p className="mt-2 text-xs text-red-600" role="alert">
              {panelError}
            </p>
          )}
          <div className="mt-3 max-w-xl">
            <label htmlFor="site-tree-parent" className="block text-xs font-medium text-slate-700">
              Rattacher sous…
            </label>
            <select
              id="site-tree-parent"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm shadow-sm transition focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 disabled:bg-slate-100"
              value={rootLocked ? '' : draftParentId}
              disabled={rootLocked || saving}
              onChange={(e) => setDraftParentId(e.target.value)}
            >
              {parentOptions.map((o) => (
                <option key={o.value || 'root'} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            {rootLocked && (
              <p className="mt-1 text-[11px] text-amber-800">
                Cette page doit rester à la racine (accueil ou hub projets).
              </p>
            )}
          </div>
          <div className="mt-4">
            <button
              type="button"
              disabled={saving || reordering || rootLocked}
              onClick={() => void handleSaveStructure()}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? 'Enregistrement…' : 'Enregistrer le parent'}
            </button>
          </div>
        </div>
      )}

      <div className="px-4 py-3">
        {error && (
          <div className="mb-3 flex gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {loading && !tree?.length && (
          <div className="flex items-center gap-2 py-8 text-sm text-slate-500">
            <RefreshCw className="h-4 w-4 animate-spin" />
            Chargement…
          </div>
        )}

        {!loading &&
          tree &&
          tree.length === 0 &&
          (!navRightRail || navRightRail.length === 0) &&
          (!globalCommonModules || globalCommonModules.length === 0) && (
          <div className="flex gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
            <Info className="h-4 w-4 shrink-0 text-slate-500" />
            Aucune page ni élément de menu à droite. Les boutons d’ajout apparaissent à droite des titres de section
            ci-dessous une fois la structure chargée.
          </div>
        )}

        {meta && meta.vaultPagesAtRoot > 0 && (
          <div className="mb-3 flex gap-2 rounded-lg border border-amber-200 bg-amber-50/90 px-3 py-2 text-xs text-amber-950">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-700" />
            <div>
              <p className="font-medium">
                {meta.vaultPagesAtRoot} offre{meta.vaultPagesAtRoot > 1 ? 's' : ''} vault à la racine
              </p>
              <p className="mt-0.5 text-amber-900/90">
                {meta.hasProjectsHub
                  ? 'Rattachez-les au hub « projects » en mode édition.'
                  : 'Créez la page « projects » comme hub.'}
              </p>
            </div>
          </div>
        )}

        {!loading && tree != null && (
          <ul className="border-t border-slate-100 pt-1">
            <StructureZone1Banner />
            {(tree.length > 0 || onAddPage) && (
              <>
                <MenuPagesZoneDivider onAddPage={onAddPage} readOnlyStructure={readOnlyStructure} />
                {tree.length > 0 ? (
                  tree.map((node) => (
                    <TreeRow
                      key={node.id}
                      node={node}
                      depth={0}
                      locale={locale}
                      collapsedIds={collapsedIds}
                      toggleCollapsed={toggleCollapsed}
                      editMode={editMode}
                      selectedId={selectedId}
                      onPickForStructure={onPickForStructure}
                      onReorderRow={editMode ? handleReorderNode : undefined}
                      reordering={reordering}
                      flashId={flashId}
                      onOpenPreview={openStructurePreview}
                      onNavigateToMenus={onNavigateToMenus}
                      onCopyDraftFromDefault={(slug, target) => setCopyDialog({ slug, target })}
                    />
                  ))
                ) : (
                  <li className="list-none border-b border-slate-50 px-3 py-2.5 text-xs text-slate-500">
                    Aucune page à la racine. Utilisez « Ajouter une page » ci-dessus pour en créer une.
                  </li>
                )}
              </>
            )}
            {(navRightRail && navRightRail.length > 0) || onAddNavButton ? (
              <>
                <NavActionsZoneHeader
                  onAddNavButton={onAddNavButton}
                  readOnlyStructure={readOnlyStructure}
                />
                {navRightRail.length > 0 &&
                  !navRightRail.some((r) => r.kind === 'language_switcher') && (
                    <li className="list-none border-b border-amber-100 bg-amber-50/80 px-3 py-2.5 text-[11px] leading-snug text-amber-950">
                      <strong className="font-semibold">Sélecteur de langue absent du menu primaire.</strong>{' '}
                      Ce n’est pas toujours une migration manquante : le plus souvent,{' '}
                      <strong className="font-semibold">
                        la base utilisée par <code className="font-mono text-[10px]">npx prisma migrate deploy</code>{' '}
                        n’est pas la même que le <code className="font-mono text-[10px]">DATABASE_URL</code> du serveur
                        Next
                      </strong>{' '}
                      (fichier <code className="font-mono text-[10px]">.env</code> vs{' '}
                      <code className="font-mono text-[10px]">.env.local</code>, ou URL « pooler » vs « direct »).
                      Vérifiez aussi les logs serveur pour{' '}
                      <code className="font-mono text-[10px]">ensurePrimaryMenuLanguageSwitcher</code>. Sinon : migration{' '}
                      <code className="rounded bg-white/80 px-1 py-px font-mono text-[10px]">
                        20260425140000_menu_item_language_switcher
                      </code>
                      , puis <strong>redémarrer</strong> le dev server et actualiser. Sur le site public, un repli peut
                      masquer le problème.
                    </li>
                  )}
                {navRightRail && navRightRail.length > 0 ? (
                  navRightRail.map((row, index) =>
                    row.kind === 'language_switcher' ? (
                      <LanguageSwitcherTreeRow
                        key={row.id}
                        id={row.id}
                        label={row.label}
                        enabled={row.enabled}
                        structureLocale={locale}
                        index={index}
                        total={navRightRail.length}
                        readOnly={readOnlyStructure || !editMode}
                        reordering={reorderingNavActions}
                        onReorder={handleReorderNavAction}
                      />
                    ) : (
                      <NavActionButtonTreeRow
                        key={row.id}
                        row={row}
                        index={index}
                        total={navRightRail.length}
                        readOnly={readOnlyStructure || !editMode}
                        reordering={reorderingNavActions}
                        onReorder={handleReorderNavAction}
                      />
                    ),
                  )
                ) : (
                  <li className="list-none border-b border-slate-50 px-3 py-2.5 text-xs text-slate-500">
                    Aucun élément chargé pour la zone droite. Actualisez ou attendez la fin du chargement.
                  </li>
                )}
              </>
            ) : null}
            {globalCommonModules.length > 0 ? (
              <>
                <li className="list-none pt-6" aria-hidden>
                  <div className="mx-1 border-t border-slate-200" />
                </li>
                <GlobalModulesZoneHeader
                  onAddCommonModule={onAddCommonModule}
                  readOnlyStructure={readOnlyStructure}
                />
                {globalCommonModules.map((row) => (
                  <GlobalCommonModuleTreeRow
                    key={row.id}
                    row={row}
                    locale={locale}
                    onOpenPreview={openCommonModulePreview}
                  />
                ))}
              </>
            ) : null}
          </ul>
        )}
      </div>
      </div>

      {previewOpen && (
        <div className="hidden min-h-0 min-w-0 flex-col lg:flex lg:h-full">
          <PagePreviewPanel
            title={previewTitle}
            previewUrl={previewUrl}
            toolbar={previewToolbar}
            onClose={closeStructurePreview}
            className="h-full min-h-0"
            reloadEpoch={previewReloadEpoch}
          />
        </div>
      )}
    </section>
    </>
  )
}
