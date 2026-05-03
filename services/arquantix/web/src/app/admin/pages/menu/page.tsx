'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { LanguageCheckActions } from '@/components/admin/LanguageCheckActions'
import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'
import { ChevronDown, ChevronUp, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MenuStructureAlignmentPanel } from '@/components/admin/MenuStructureAlignmentPanel'
import {
  computeMenuEditorPolicy,
  selectMenuNameToDisplay,
} from '@/lib/admin/menuEditorPolicy'
import { selectActiveLocaleEditsForSave } from '@/lib/admin/menuSaveLocale'

const LOCALE_LABEL: Record<Locale, string> = {
  fr: 'Français',
  en: 'English',
  it: 'Italiano',
}

interface Page {
  id: string
  slug: string
  title: string | null
  computedUrlPath: string
}

interface MenuItemI18n {
  id: string
  locale: string
  label: string
  translationStatus: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
}

interface MenuItem {
  id: string
  label: string
  labelBase?: string
  type: 'LINK' | 'BUTTON'
  isRoot: boolean
  pageId: string | null
  page: Page | null
  computedUrlPath: string | null
  isInvalidTarget?: boolean
  order: number
  enabled: boolean
  buttonStyle?: string | null
  buttonAction?: string | null
  externalUrl?: string | null
  i18n?: MenuItemI18n[]
}

interface MenuI18n {
  id: string
  locale: string
  name: string
  translationStatus: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
}

interface Menu {
  id: string
  key: string
  name: string
  nameBase?: string
  i18n?: MenuI18n[]
  items: MenuItem[]
}

export default function AdminMenuPage() {
  const router = useRouter()
  const [menu, setMenu] = useState<Menu | null>(null)
  const [pages, setPages] = useState<Page[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [menuName, setMenuName] = useState('')
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState<string | null>(null)
  const [expandedI18nItems, setExpandedI18nItems] = useState<Set<string>>(new Set())
  const [expandedMenuI18n, setExpandedMenuI18n] = useState(false)
  const [i18nLabels, setI18nLabels] = useState<Record<string, Record<string, string>>>({}) // itemId -> locale -> label
  const [i18nStatuses, setI18nStatuses] = useState<Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>>>({})
  const [menuI18nNames, setMenuI18nNames] = useState<Record<string, string>>({}) // locale -> name
  const [menuI18nStatuses, setMenuI18nStatuses] = useState<Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>>({})
  const [showTranslateModal, setShowTranslateModal] = useState<string | null>(null) // menuItemId
  const [showMenuTranslateModal, setShowMenuTranslateModal] = useState(false)
  const [savingI18n, setSavingI18n] = useState<Record<string, boolean>>({})
  const [savingMenuI18n, setSavingMenuI18n] = useState(false)
  const [approving, setApproving] = useState<Record<string, string>>({}) // itemId -> locale
  const [approvingMenu, setApprovingMenu] = useState<string>('') // locale
  /**
   * Locale unique pilotant l'éditeur (alignement UX strict avec
   * `SiteFooterEditor.activeLocale`) :
   *   - libellés affichés (refetch avec `?locale=${activeLocale}`),
   *   - bouton « Copier depuis FR » (cible = activeLocale),
   *   - bandeau Contrôle linguistique (scan + apply pour activeLocale),
   *   - verrouillage de la structure (lecture seule quand ≠ defaultLocale).
   */
  const [activeLocale, setActiveLocale] = useState<Locale>(defaultLocale as Locale)
  const [copyLocaleDialog, setCopyLocaleDialog] = useState<Locale | null>(null)
  const [copyLocaleMode, setCopyLocaleMode] = useState<'missing' | 'overwrite'>('missing')
  const [copyingLocale, setCopyingLocale] = useState(false)
  /**
   * Bouton « Tout enregistrer pour cette locale » — équivalent du bouton
   * « Enregistrer » du `SiteFooterEditor`. Persiste en une seule transaction
   * tous les inputs inline en mémoire (`menuName`, `menuI18nNames[locale]`,
   * `i18nLabels[*][locale]`) via `POST /api/admin/menus/[key]/save-locale`.
   */
  const [savingLocale, setSavingLocale] = useState(false)
  /**
   * Politique d'édition unique (source de vérité testée et partagée avec
   * `menuEditorPolicy.test.ts`). Cf. `lib/admin/menuEditorPolicy.ts` pour
   * les invariants : structure verrouillée hors `defaultLocale`, copie
   * pertinente uniquement quand `activeLocale !== defaultLocale`, etc.
   */
  const policy = computeMenuEditorPolicy(activeLocale, defaultLocale as Locale)
  const { isStructureLocked } = policy
  const [newItem, setNewItem] = useState({
    label: '',
    type: 'LINK' as 'LINK' | 'BUTTON',
    isRoot: false,
    pageId: '',
    enabled: true,
    buttonStyle: 'primary',
    buttonAction: '',
    externalUrl: '',
  })

  useEffect(() => {
    fetchPages()
  }, [])

  // Refetch menu chaque fois que la locale active change : le serveur
  // résout `Menu.name` / `MenuItem.label` via `resolveLabelWithFallback`
  // et renvoie les libellés vus par un visiteur dans cette locale.
  useEffect(() => {
    fetchMenu(activeLocale)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLocale])

  const handleCopyLocaleConfirm = async () => {
    if (!menu || !copyLocaleDialog) return
    setCopyingLocale(true)
    try {
      const res = await fetch(
        `/api/admin/menus/${encodeURIComponent(menu.key)}/copy-locale`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sourceLocale: defaultLocale,
            targetLocale: copyLocaleDialog,
            mode: copyLocaleMode,
          }),
        },
      )
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Échec de la copie')
      }
      const s = data.summary ?? {}
      const parts: string[] = []
      if (s.menuName === 'copied') parts.push('nom du menu copié')
      else if (s.menuName === 'skippedExisting') parts.push('nom du menu préservé')
      parts.push(`${s.itemsCopied ?? 0} item(s) copié(s)`)
      if (s.itemsSkippedExisting) parts.push(`${s.itemsSkippedExisting} préservé(s)`)
      if (s.itemsSkippedDisabled) parts.push(`${s.itemsSkippedDisabled} désactivé(s)`)
      toastSuccess(
        `Copié ${defaultLocale.toUpperCase()} → ${copyLocaleDialog.toUpperCase()} : ${parts.join(', ')}.`,
      )
      const justCopiedTo = copyLocaleDialog
      setCopyLocaleDialog(null)
      // Bascule automatique sur la locale qu'on vient de remplir (alignement
      // Footer : « Copier depuis FR » s'effectue en restant dans le contexte
      // de la locale ciblée).
      if (justCopiedTo !== activeLocale) {
        setActiveLocale(justCopiedTo)
      } else {
        await fetchMenu(activeLocale)
      }
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur de copie')
    } finally {
      setCopyingLocale(false)
    }
  }

  /**
   * Persiste en bulk pour `activeLocale` toutes les éditions inline en
   * mémoire (input « Menu Name », accordéons « Localized Names »/«Localized
   * Labels »). Évite à l'opérateur d'avoir à cliquer N petits boutons
   * individuels par locale × item — alignement strict Footer
   * (`SiteFooterEditor.handleSave`). Idempotent côté serveur.
   */
  const handleSaveAllLocale = async () => {
    if (!menu) return
    setSavingLocale(true)
    try {
      const { itemLabels, menuI18nName } = selectActiveLocaleEditsForSave({
        activeLocale,
        i18nLabels,
        menuI18nNames,
      })
      const res = await fetch(
        `/api/admin/menus/${encodeURIComponent(menu.key)}/save-locale`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            activeLocale,
            defaultLocale,
            menuNameInput:
              activeLocale === (defaultLocale as Locale) ? menuName : undefined,
            menuI18nName,
            itemLabels,
          }),
        },
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.error || 'Échec de l’enregistrement')
      }
      const s = data.summary ?? {}
      const parts: string[] = []
      if (s.menuNameUpdated) parts.push('nom de base')
      if (s.menuI18nNameUpdated) parts.push('nom localisé')
      parts.push(`${s.itemsWritten ?? 0} libellé(s) item`)
      if (s.itemsSkippedEmpty)
        parts.push(`${s.itemsSkippedEmpty} ignoré(s) (vides)`)
      toastSuccess(
        `Enregistré pour ${activeLocale.toUpperCase()} : ${parts.join(', ')}.`,
      )
      await fetchMenu(activeLocale)
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur d’enregistrement')
    } finally {
      setSavingLocale(false)
    }
  }

  const fetchMenu = async (locale: Locale = activeLocale) => {
    try {
      const response = await fetch(`/api/admin/menus/primary?locale=${encodeURIComponent(locale)}`)
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch menu')
      }

      const data = await response.json()
      setMenu(data.menu)
      // Sur la locale par défaut on édite `Menu.name` (base, partagé) ;
      // sur les autres locales le champ est en lecture seule et affiche la
      // valeur résolue par le serveur. Helper testé dans `menuEditorPolicy`.
      setMenuName(
        selectMenuNameToDisplay({
          activeLocale: locale,
          defaultLocale: defaultLocale as Locale,
          nameBase: data.menu.nameBase ?? '',
          resolvedName: data.menu.name ?? '',
        }),
      )
      
      // Initialize i18n labels and statuses for menu items
      const labels: Record<string, Record<string, string>> = {}
      const statuses: Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>> = {}
      
      data.menu.items.forEach((item: MenuItem) => {
        if (item.i18n) {
          labels[item.id] = {}
          statuses[item.id] = {}
          item.i18n.forEach((i18n) => {
            labels[item.id][i18n.locale] = i18n.label
            statuses[item.id][i18n.locale] = i18n.translationStatus
          })
        }
      })
      
      setI18nLabels(labels)
      setI18nStatuses(statuses)

      // Initialize i18n names and statuses for menu
      const menuNames: Record<string, string> = {}
      const menuStatuses: Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'> = {}
      
      if (data.menu.i18n) {
        data.menu.i18n.forEach((i18n: MenuI18n) => {
          menuNames[i18n.locale] = i18n.name
          menuStatuses[i18n.locale] = i18n.translationStatus
        })
      }
      
      setMenuI18nNames(menuNames)
      setMenuI18nStatuses(menuStatuses)
    } catch (error) {
      console.error('Error fetching menu:', error)
      toastError('Failed to load menu')
    } finally {
      setLoading(false)
    }
  }

  const fetchMenuItemI18n = async (itemId: string) => {
    try {
      const response = await fetch(`/api/admin/menu-items/${itemId}/i18n`)
      if (!response.ok) {
        throw new Error('Failed to fetch i18n')
      }
      const data = await response.json()
      
      // Update local state
      setI18nLabels((prev) => {
        const newLabels = { ...prev }
        if (!newLabels[itemId]) newLabels[itemId] = {}
        data.i18n.forEach((i18n: MenuItemI18n) => {
          newLabels[itemId][i18n.locale] = i18n.label
        })
        return newLabels
      })
      
      setI18nStatuses((prev) => {
        const newStatuses = { ...prev }
        if (!newStatuses[itemId]) newStatuses[itemId] = {}
        data.i18n.forEach((i18n: MenuItemI18n) => {
          newStatuses[itemId][i18n.locale] = i18n.translationStatus
        })
        return newStatuses
      })
    } catch (error) {
      console.error('Error fetching menu item i18n:', error)
    }
  }

  const handleSaveI18nLabel = async (itemId: string, locale: string) => {
    const label = i18nLabels[itemId]?.[locale]
    if (!label || label.trim().length === 0) {
      toastError('Label cannot be empty')
      return
    }

    setSavingI18n((prev) => ({ ...prev, [itemId]: true }))
    try {
      const response = await fetch(`/api/admin/menu-items/${itemId}/i18n`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locale, label }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to save label')
      }

      toastSuccess('Label saved')
      await fetchMenuItemI18n(itemId)
    } catch (error: any) {
      toastError(error.message || 'Failed to save label')
    } finally {
      setSavingI18n((prev) => ({ ...prev, [itemId]: false }))
    }
  }

  const handleApproveTranslation = async (itemId: string, locale: string) => {
    setApproving((prev) => ({ ...prev, [`${itemId}:${locale}`]: 'true' }))
    try {
      const response = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: 'MENU_ITEM',
          entityId: itemId,
          locale,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to approve translation')
      }

      toastSuccess('Translation approved')
      await fetchMenuItemI18n(itemId)
    } catch (error: any) {
      toastError(error.message || 'Failed to approve translation')
    } finally {
      setApproving((prev) => {
        const newApproving = { ...prev }
        delete newApproving[`${itemId}:${locale}`]
        return newApproving
      })
    }
  }

  const toggleI18nExpanded = (itemId: string) => {
    setExpandedI18nItems((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(itemId)) {
        newSet.delete(itemId)
      } else {
        newSet.add(itemId)
        // Fetch i18n when expanding
        fetchMenuItemI18n(itemId)
      }
      return newSet
    })
  }

  const fetchMenuI18n = async () => {
    if (!menu) return
    try {
      const response = await fetch(`/api/admin/menus/${menu.key}/i18n`)
      if (!response.ok) {
        throw new Error('Failed to fetch menu i18n')
      }
      const data = await response.json()
      
      // Update local state
      const newNames: Record<string, string> = {}
      const newStatuses: Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'> = {}
      
      data.i18n.forEach((i18n: MenuI18n) => {
        newNames[i18n.locale] = i18n.name
        newStatuses[i18n.locale] = i18n.translationStatus
      })
      
      setMenuI18nNames((prev) => ({ ...prev, ...newNames }))
      setMenuI18nStatuses((prev) => ({ ...prev, ...newStatuses }))
    } catch (error) {
      console.error('Error fetching menu i18n:', error)
    }
  }

  const handleSaveMenuI18nName = async (locale: string) => {
    if (!menu) return
    const name = menuI18nNames[locale]
    if (!name || name.trim().length === 0) {
      toastError('Name cannot be empty')
      return
    }

    setSavingMenuI18n(true)
    try {
      const response = await fetch(`/api/admin/menus/${menu.key}/i18n`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locale, name }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to save name')
      }

      toastSuccess('Name saved')
      await fetchMenuI18n()
    } catch (error: any) {
      toastError(error.message || 'Failed to save name')
    } finally {
      setSavingMenuI18n(false)
    }
  }

  const handleApproveMenuTranslation = async (locale: string) => {
    if (!menu) return
    setApprovingMenu(locale)
    try {
      const response = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: 'MENU',
          entityId: menu.id,
          locale,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to approve translation')
      }

      toastSuccess('Translation approved')
      await fetchMenuI18n()
    } catch (error: any) {
      toastError(error.message || 'Failed to approve translation')
    } finally {
      setApprovingMenu('')
    }
  }

  const fetchPages = async () => {
    try {
      const response = await fetch('/api/admin/pages')
      if (!response.ok) {
        throw new Error('Failed to fetch pages')
      }

      const data = await response.json()
      setPages(data.pages || [])
    } catch (error) {
      console.error('Error fetching pages:', error)
    }
  }

  const handleSaveMenuName = async () => {
    if (!menu) return

    setSaving(true)
    try {
      const response = await fetch('/api/admin/menus/primary', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: menuName }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to update menu name')
      }

      toastSuccess('Saved')
      await fetchMenu()
    } catch (error: any) {
      toastError(error.message || 'Failed to save menu name')
    } finally {
      setSaving(false)
    }
  }

  const handleAddItem = async () => {
    if (!menu) return

    setSaving(true)
    try {
      const payload: any = {
        label: newItem.label,
        type: newItem.type,
        enabled: newItem.enabled,
      }

      if (newItem.type === 'BUTTON') {
        payload.buttonStyle = newItem.buttonStyle
        payload.buttonAction = newItem.buttonAction
        payload.externalUrl = newItem.externalUrl || null
      } else {
        payload.isRoot = newItem.isRoot
        if (!newItem.isRoot) {
          if (!newItem.pageId) {
            toastError('Please select a page target')
            setSaving(false)
            return
          }
          payload.pageId = newItem.pageId
        }
      }

      const response = await fetch('/api/admin/menus/primary/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to add menu item')
      }

      toastSuccess('Menu item added')
      setShowAddModal(false)
      setNewItem({ label: '', type: 'LINK', isRoot: false, pageId: '', enabled: true, buttonStyle: 'primary', buttonAction: '', externalUrl: '' })
      await fetchMenu()
    } catch (error: any) {
      toastError(error.message || 'Failed to add menu item')
    } finally {
      setSaving(false)
    }
  }

  const handleUpdateItem = async (item: MenuItem) => {
    if (!menu) return

    setSaving(true)
    try {
      const payload: any = {
        label: item.label,
        type: item.type,
        enabled: item.enabled,
      }

      if (item.type === 'BUTTON') {
        payload.buttonStyle = item.buttonStyle
        payload.buttonAction = item.buttonAction
        payload.externalUrl = item.externalUrl || null
      } else {
        payload.isRoot = item.isRoot
        if (!item.isRoot) {
          if (!item.pageId) {
            toastError('Please select a page target')
            setSaving(false)
            return
          }
          payload.pageId = item.pageId
        } else {
          payload.pageId = null
        }
      }

      const response = await fetch(`/api/admin/menus/primary/items/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to update menu item')
      }

      toastSuccess('Saved')
      await fetchMenu()
      setEditingItem(null)
    } catch (error: any) {
      toastError(error.message || 'Failed to update menu item')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteItem = async (itemId: string) => {
    if (!menu) return

    try {
      const response = await fetch(`/api/admin/menus/primary/items/${itemId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete menu item')
      }

      toastSuccess('Deleted')
      await fetchMenu()
    } catch (error: any) {
      throw error // Let ConfirmDialog handle the error toast
    }
  }

  const handleMoveUp = async (index: number) => {
    if (!menu || index === 0) return

    const items = [...menu.items]
    const temp = items[index]
    items[index] = items[index - 1]
    items[index - 1] = temp

    await handleReorder(items.map((item) => item.id))
  }

  const handleMoveDown = async (index: number) => {
    if (!menu || index === menu.items.length - 1) return

    const items = [...menu.items]
    const temp = items[index]
    items[index] = items[index + 1]
    items[index + 1] = temp

    await handleReorder(items.map((item) => item.id))
  }

  const handleReorder = async (orderedItemIds: string[]) => {
    setSaving(true)
    try {
      const response = await fetch('/api/admin/menus/primary/items/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orderedItemIds }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to reorder items')
      }

      toastSuccess('Order updated')
      await fetchMenu()
    } catch (error: any) {
      toastError(error.message || 'Failed to reorder items')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading menu...</div>
      </div>
    )
  }

  if (!menu) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Menu not found.</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Menu Manager</h1>
          <p className="text-sm text-gray-500 mt-1">Manage navigation menu items</p>
        </div>
        <Link
          href="/admin/pages"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Structure du site
        </Link>
      </div>

      <MenuStructureAlignmentPanel
        active={!loading && !!menu}
        onApplied={async () => {
          await fetchMenu(activeLocale)
        }}
      />

      {/* ----------------------------------------------------------------- */}
      {/* Bandeau unifié « édition par locale » — alignement strict Footer.  */}
      {/* Pilote : libellés affichés, bouton Copier, Contrôle linguistique.  */}
      {/* ----------------------------------------------------------------- */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
        <div className="flex flex-col gap-4 rounded-lg border border-indigo-100 bg-indigo-50/50 p-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-indigo-900">
              Langue éditée
            </label>
            <select
              value={activeLocale}
              onChange={(e) => setActiveLocale(e.target.value as Locale)}
              className="rounded-md border border-indigo-200 bg-white px-3 py-2 text-sm font-medium text-gray-900 shadow-sm"
              aria-label="Langue du menu à éditer"
              disabled={loading || saving || copyingLocale}
            >
              {supportedLocales.map((loc) => (
                <option key={loc} value={loc}>
                  {LOCALE_LABEL[loc]} ({loc})
                </option>
              ))}
            </select>
            <p className="mt-1 max-w-xs text-xs text-gray-600">
              Bascule entre {supportedLocales.map((l) => l.toUpperCase()).join(' / ')}. Les libellés affichés
              correspondent à la langue éditée.
            </p>
          </div>

          <div className="flex flex-col items-end gap-2">
            <label className="flex items-center gap-2 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={copyLocaleMode === 'overwrite'}
                onChange={(e) =>
                  setCopyLocaleMode(e.target.checked ? 'overwrite' : 'missing')
                }
                className="rounded border-slate-300"
                disabled={activeLocale === (defaultLocale as Locale)}
              />
              <span>
                Écraser les libellés existants
                {copyLocaleMode === 'overwrite' ? (
                  <span className="ml-1 rounded bg-red-100 px-1 text-[10px] font-semibold uppercase text-red-700">
                    destructif
                  </span>
                ) : null}
              </span>
            </label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setCopyLocaleDialog(activeLocale)}
              disabled={
                loading ||
                saving ||
                copyingLocale ||
                !menu ||
                activeLocale === (defaultLocale as Locale)
              }
              title={
                activeLocale === (defaultLocale as Locale)
                  ? `Vous éditez déjà ${LOCALE_LABEL[defaultLocale as Locale]} : la copie est inutile.`
                  : `Matérialise les libellés ${defaultLocale.toUpperCase()} dans MenuI18n[${activeLocale}] / MenuItemI18n[${activeLocale}].`
              }
              className="w-full sm:w-auto"
            >
              <Copy className="mr-2 h-4 w-4" />
              Copier depuis {LOCALE_LABEL[defaultLocale as Locale]}
            </Button>
          </div>
        </div>

        {isStructureLocked ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
            <strong className="font-medium">Structure verrouillée.</strong> Vous éditez la locale{' '}
            <strong>{LOCALE_LABEL[activeLocale]}</strong> ({activeLocale.toUpperCase()}).
            Pour ajouter / supprimer / réordonner des items, modifier le type, la page cible, l&apos;URL externe
            ou l&apos;activation, basculez sur <strong>{LOCALE_LABEL[defaultLocale as Locale]}</strong>. Seuls
            les libellés (nom du menu, label des items) peuvent être édités sur cette locale, via le panneau
            « Localized Labels » de chaque item, le bouton « Copier depuis FR » ci-dessus, ou le contrôle
            linguistique IA.
          </div>
        ) : null}

        {/* Contrôle linguistique — branché sur la même activeLocale (un seul concept). */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50/70 px-4 py-3">
          <div className="text-xs text-slate-600">
            <p className="font-semibold uppercase tracking-wide text-slate-700">
              Contrôle linguistique
            </p>
            <p className="mt-1 max-w-md leading-snug">
              Analyse exhaustive du nom du menu + de tous les libellés d&apos;items activés
              (détection IA des cas ambigus), puis correction OpenAI directe pour la langue éditée
              (upsert MenuI18n / MenuItemI18n, statut MACHINE).
            </p>
          </div>
          {menu ? (
            <LanguageCheckActions
              domainLabel="menu"
              scanUrl={`/api/admin/menus/${menu.key}/check-language/scan`}
              applyUrl={`/api/admin/menus/${menu.key}/check-language/apply`}
              activeLocale={activeLocale}
              localeLabel={LOCALE_LABEL[activeLocale]}
              onApplied={() => fetchMenu(activeLocale)}
              disabled={loading || saving || copyingLocale || savingLocale}
            />
          ) : null}
        </div>

        {/* ------------------------------------------------------------- */}
        {/* « Tout enregistrer pour la locale active » — équivalent du    */}
        {/* bouton « Enregistrer » du SiteFooterEditor. Pousse en bulk     */}
        {/* `Menu.name` (uniquement si activeLocale = defaultLocale),      */}
        {/* `MenuI18n[locale].name` et tous les `MenuItemI18n[locale]`     */}
        {/* déjà chargés/édités. Évite d'oublier un Save inline.           */}
        {/* ------------------------------------------------------------- */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50/70 px-4 py-3">
          <div className="text-xs text-emerald-900">
            <p className="font-semibold uppercase tracking-wide text-emerald-800">
              Enregistrer toutes les modifications de {LOCALE_LABEL[activeLocale]}
            </p>
            <p className="mt-1 max-w-md leading-snug">
              Pousse en une seule transaction le nom du menu et tous les libellés
              d&apos;items édités pour cette locale. Statut <strong>ORIGINAL</strong>
              {' '}(édition humaine). Visible immédiatement côté navigation publique.
            </p>
          </div>
          <Button
            type="button"
            onClick={handleSaveAllLocale}
            disabled={
              loading || saving || savingLocale || copyingLocale || !menu
            }
            className="w-full sm:w-auto"
            title={
              `Persistance en bulk pour ${activeLocale.toUpperCase()} : Menu.name (si ${defaultLocale.toUpperCase()}), MenuI18n et MenuItemI18n.`
            }
          >
            {savingLocale
              ? 'Enregistrement…'
              : `Enregistrer pour ${activeLocale.toUpperCase()}`}
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={copyLocaleDialog !== null}
        onOpenChange={(open) => {
          if (!open && !copyingLocale) setCopyLocaleDialog(null)
        }}
        title={
          copyLocaleDialog
            ? `Copier ${defaultLocale.toUpperCase()} → ${copyLocaleDialog.toUpperCase()} (${
                copyLocaleMode === 'missing' ? 'préserve l’existant' : 'écrase tout'
              })`
            : 'Copier les libellés vers une autre langue'
        }
        description={
          copyLocaleDialog
            ? `Matérialise les libellés ${defaultLocale.toUpperCase()} dans MenuI18n / MenuItemI18n pour ${copyLocaleDialog.toUpperCase()} (statut ORIGINAL). ${
                copyLocaleMode === 'missing'
                  ? 'Les libellés cibles déjà présents sont préservés.'
                  : 'Tous les libellés cibles existants seront écrasés.'
              } Étape préalable au scan + correction IA.`
            : ''
        }
        confirmLabel={copyingLocale ? 'Copie…' : 'Copier'}
        cancelLabel="Annuler"
        destructive={copyLocaleMode === 'overwrite'}
        onConfirm={handleCopyLocaleConfirm}
      />

      {/* Menu Name — édition uniquement sur la locale par défaut (structure partagée). */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4">
          Primary Menu
          {isStructureLocked ? (
            <span className="ml-2 align-middle text-xs font-normal text-amber-700">
              (lecture seule — locale {activeLocale.toUpperCase()})
            </span>
          ) : null}
        </h2>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Menu Name
              {isStructureLocked ? (
                <span className="ml-1 text-xs text-gray-500">
                  — affiche la valeur résolue pour {activeLocale.toUpperCase()}
                </span>
              ) : null}
            </label>
            <input
              type="text"
              value={menuName}
              onChange={(e) => setMenuName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-50 disabled:text-gray-500"
              disabled={isStructureLocked}
              readOnly={isStructureLocked}
            />
          </div>
          <button
            onClick={handleSaveMenuName}
            disabled={saving || isStructureLocked}
            className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            title={
              isStructureLocked
                ? `Le nom de base se modifie uniquement depuis ${LOCALE_LABEL[defaultLocale as Locale]}.`
                : undefined
            }
          >
            {saving ? 'Saving...' : 'Save Name'}
          </button>
        </div>
      </div>

      {/* Menu Items */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold">Menu Items</h2>
          <button
            onClick={() => setShowAddModal(true)}
            disabled={isStructureLocked}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            title={
              isStructureLocked
                ? `Ajout d'item disponible uniquement depuis ${LOCALE_LABEL[defaultLocale as Locale]}.`
                : undefined
            }
          >
            + Add Menu Item
          </button>
        </div>

        {menu.items.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No menu items yet. Add your first item!</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Order</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Type</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Label</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Target</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">URL</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Enabled</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {menu.items.map((item, index) => {
                  const isInvalid = item.isInvalidTarget === true
                  return (
                    <>
                    <tr
                      key={item.id}
                      className={`border-b border-gray-100 hover:bg-gray-50 ${
                        isInvalid ? 'bg-red-50' : ''
                      }`}
                    >
                      <td className="py-3 px-4">
                        <div className="flex flex-col gap-1">
                          {index > 0 && (
                            <button
                              onClick={() => handleMoveUp(index)}
                              disabled={saving || isStructureLocked}
                              className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-xs"
                              title={
                                isStructureLocked
                                  ? `Réordonnancement uniquement depuis ${LOCALE_LABEL[defaultLocale as Locale]}.`
                                  : 'Move up'
                              }
                            >
                              ↑
                            </button>
                          )}
                          {index < menu.items.length - 1 && (
                            <button
                              onClick={() => handleMoveDown(index)}
                              disabled={saving || isStructureLocked}
                              className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-xs"
                              title={
                                isStructureLocked
                                  ? `Réordonnancement uniquement depuis ${LOCALE_LABEL[defaultLocale as Locale]}.`
                                  : 'Move down'
                              }
                            >
                              ↓
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {editingItem?.id === item.id ? (
                          <input
                            type="text"
                            value={editingItem.label}
                            onChange={(e) =>
                              setEditingItem({ ...editingItem, label: e.target.value })
                            }
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                          />
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{item.label}</span>
                            {isInvalid && (
                              <span className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 rounded">
                                Invalid target
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {editingItem?.id === item.id ? (
                          editingItem.type === 'BUTTON' ? (
                            <div className="space-y-2">
                              <div>
                                <label className="block text-xs text-gray-600 mb-1">Button Style</label>
                                <select
                                  value={editingItem.buttonStyle || 'primary'}
                                  onChange={(e) =>
                                    setEditingItem({ ...editingItem, buttonStyle: e.target.value })
                                  }
                                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                                >
                                  <option value="primary">Primary</option>
                                  <option value="secondary">Secondary</option>
                                  <option value="outline">Outline</option>
                                </select>
                              </div>
                              <div>
                                <label className="block text-xs text-gray-600 mb-1">External URL</label>
                                <input
                                  type="url"
                                  value={editingItem.externalUrl || ''}
                                  onChange={(e) =>
                                    setEditingItem({ ...editingItem, externalUrl: e.target.value })
                                  }
                                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                                  placeholder="https://example.com"
                                />
                              </div>
                              <div>
                                <label className="block text-xs text-gray-600 mb-1">Action</label>
                                <input
                                  type="text"
                                  value={editingItem.buttonAction || ''}
                                  onChange={(e) =>
                                    setEditingItem({ ...editingItem, buttonAction: e.target.value })
                                  }
                                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                                  placeholder="onClick handler"
                                />
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-2">
                              <label className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={editingItem.isRoot}
                                  onChange={(e) => {
                                    const newIsRoot = e.target.checked
                                    setEditingItem({
                                      ...editingItem,
                                      isRoot: newIsRoot,
                                      pageId: newIsRoot ? null : editingItem.pageId,
                                    })
                                  }}
                                  className="rounded"
                                />
                                <span className="text-xs">Use site root (/)</span>
                              </label>
                              {!editingItem.isRoot && (
                                <select
                                  value={editingItem.pageId || ''}
                                  onChange={(e) =>
                                    setEditingItem({ ...editingItem, pageId: e.target.value || null })
                                  }
                                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                                >
                                  <option value="">Select a page...</option>
                                  {pages.map((page) => (
                                    <option key={page.id} value={page.id}>
                                      {page.title || page.slug} — {page.computedUrlPath}
                                    </option>
                                  ))}
                                </select>
                              )}
                            </div>
                          )
                        ) : (
                          item.type === 'BUTTON' ? (
                            <div className="text-sm text-gray-600">
                              {item.externalUrl ? (
                                <a href={item.externalUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs">
                                  {item.externalUrl}
                                </a>
                              ) : (
                                <span>Button ({item.buttonStyle || 'primary'})</span>
                              )}
                            </div>
                          ) : item.isRoot ? (
                            <span className="text-sm text-gray-600">Use site root (/)</span>
                          ) : item.page ? (
                            <span className="text-sm text-gray-600">
                              {item.page.title || item.page.slug} — {item.computedUrlPath}
                            </span>
                          ) : (
                            <span className="text-sm text-red-600">⚠️ Invalid (no page)</span>
                          )
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {item.type === 'BUTTON' ? (
                          <span className="text-sm text-gray-400">—</span>
                        ) : (
                          <span className="text-sm font-mono text-gray-600">
                            {isInvalid ? '—' : item.computedUrlPath || '—'}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {editingItem?.id === item.id ? (
                          <label className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={editingItem.enabled}
                              onChange={(e) =>
                                setEditingItem({ ...editingItem, enabled: e.target.checked })
                              }
                              className="rounded"
                            />
                            <span className="text-xs">Enabled</span>
                          </label>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="text-sm">{item.enabled ? '✓' : '✗'}</span>
                            {isInvalid && item.enabled && (
                              <span className="text-xs text-yellow-600">⚠️ Should be disabled</span>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {editingItem?.id === item.id ? (
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleUpdateItem(editingItem)}
                              disabled={saving}
                              className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingItem(null)}
                              className="px-3 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            {isInvalid && (
                              <button
                                onClick={() => setEditingItem({ ...item })}
                                disabled={isStructureLocked}
                                className="px-3 py-1 text-xs bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                title={
                                  isStructureLocked
                                    ? `Édition de la cible uniquement depuis ${LOCALE_LABEL[defaultLocale as Locale]}.`
                                    : 'Fix invalid target'
                                }
                              >
                                Fix
                              </button>
                            )}
                            <button
                              onClick={() => setEditingItem({ ...item })}
                              disabled={isStructureLocked}
                              className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                              title={
                                isStructureLocked
                                  ? `Édition de la structure uniquement depuis ${LOCALE_LABEL[defaultLocale as Locale]}. Pour modifier les libellés ${activeLocale.toUpperCase()}, utilisez le panneau « Localized Labels » ci-dessous.`
                                  : 'Edit item structure'
                              }
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => toggleI18nExpanded(item.id)}
                              className="px-3 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700"
                              title="Edit localized labels"
                            >
                              {expandedI18nItems.has(item.id) ? (
                                <ChevronUp className="w-3 h-3 inline" />
                              ) : (
                                <ChevronDown className="w-3 h-3 inline" />
                              )}
                            </button>
                            <button
                              onClick={() => setShowDeleteDialog(item.id)}
                              disabled={isStructureLocked}
                              className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                              title={
                                isStructureLocked
                                  ? `Suppression d'item uniquement depuis ${LOCALE_LABEL[defaultLocale as Locale]}.`
                                  : 'Delete item'
                              }
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                    {/* I18n Section (expandable) */}
                    <tr>
                      <td colSpan={6} className="p-0">
                        <div className={`overflow-hidden transition-all ${expandedI18nItems.has(item.id) ? 'max-h-[500px]' : 'max-h-0'}`}>
                          <div className="px-4 py-4 bg-gray-50 border-t border-gray-200">
                            <div className="flex items-center justify-between mb-3">
                              <h4 className="text-sm font-semibold text-gray-700">Localized Labels</h4>
                              <button
                                onClick={() => toggleI18nExpanded(item.id)}
                                className="text-xs text-gray-500 hover:text-gray-700"
                              >
                                {expandedI18nItems.has(item.id) ? (
                                  <ChevronUp className="w-4 h-4" />
                                ) : (
                                  <ChevronDown className="w-4 h-4" />
                                )}
                              </button>
                            </div>
                            
                            {expandedI18nItems.has(item.id) && (
                              <div className="space-y-3">
                                {supportedLocales.map((locale) => {
                                  const currentLabel = i18nLabels[item.id]?.[locale] || ''
                                  const status = i18nStatuses[item.id]?.[locale] || 'ORIGINAL'
                                  const isSaving = savingI18n[item.id]
                                  const isApproving = approving[`${item.id}:${locale}`]
                                  
                                  return (
                                    <div key={locale} className="bg-white p-3 rounded border border-gray-200">
                                      <div className="flex items-center gap-2 mb-2">
                                        <span className="text-xs font-medium text-gray-700 uppercase">{locale}</span>
                                        {status === 'ORIGINAL' && (
                                          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">ORIGINAL</span>
                                        )}
                                        {status === 'MACHINE' && (
                                          <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-800 rounded">MACHINE</span>
                                        )}
                                        {status === 'APPROVED' && (
                                          <span className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded">APPROVED</span>
                                        )}
                                      </div>
                                      
                                      <div className="flex gap-2 mb-2">
                                        <input
                                          type="text"
                                          value={currentLabel}
                                          onChange={(e) => {
                                            setI18nLabels((prev) => ({
                                              ...prev,
                                              [item.id]: {
                                                ...prev[item.id],
                                                [locale]: e.target.value,
                                              },
                                            }))
                                          }}
                                          className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded"
                                          placeholder={`Label for ${locale.toUpperCase()}`}
                                        />
                                        <button
                                          onClick={() => handleSaveI18nLabel(item.id, locale)}
                                          disabled={isSaving || !currentLabel.trim()}
                                          className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                                        >
                                          {isSaving ? 'Saving...' : 'Save'}
                                        </button>
                                        {status === 'MACHINE' && (
                                          <button
                                            onClick={() => handleApproveTranslation(item.id, locale)}
                                            disabled={!!isApproving}
                                            className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                                          >
                                            {isApproving ? 'Approving...' : 'Approve'}
                                          </button>
                                        )}
                                      </div>
                                      
                                      <p className="text-xs text-gray-500">
                                        This label is displayed in the site navigation for the selected language.
                                      </p>
                                    </div>
                                  )
                                })}
                                
                                <div className="pt-2 border-t border-gray-200">
                                  <button
                                    onClick={() => setShowTranslateModal(item.id)}
                                    className="px-4 py-2 text-sm bg-purple-600 text-white rounded hover:bg-purple-700"
                                  >
                                    Auto-translate
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold mb-4">Add Menu Item</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Label *</label>
                <input
                  type="text"
                  value={newItem.label}
                  onChange={(e) => setNewItem({ ...newItem, label: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="About"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
                <select
                  value={newItem.type}
                  onChange={(e) => {
                    const newType = e.target.value as 'LINK' | 'BUTTON'
                    setNewItem({
                      ...newItem,
                      type: newType,
                      isRoot: newType === 'BUTTON' ? false : newItem.isRoot,
                      pageId: newType === 'BUTTON' ? '' : newItem.pageId,
                    })
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="LINK">Link (navigation item)</option>
                  <option value="BUTTON">Button (right side)</option>
                </select>
              </div>

              {newItem.type === 'LINK' ? (
                <>
                  <div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={newItem.isRoot}
                        onChange={(e) => {
                          const isRoot = e.target.checked
                          setNewItem({
                            ...newItem,
                            isRoot,
                            pageId: isRoot ? '' : newItem.pageId,
                          })
                        }}
                        className="rounded"
                      />
                      <span className="text-sm font-medium">Use site root (/)</span>
                    </label>
                    {newItem.isRoot && (
                      <p className="text-xs text-gray-500 mt-1 ml-6">
                        When checked, URL will be &quot;/&quot;
                      </p>
                    )}
                  </div>

                  {!newItem.isRoot && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Page target *
                      </label>
                      <select
                        value={newItem.pageId}
                        onChange={(e) => setNewItem({ ...newItem, pageId: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="">Select a page...</option>
                        {pages.map((page) => (
                          <option key={page.id} value={page.id}>
                            {page.title || page.slug} — {page.computedUrlPath}
                          </option>
                        ))}
                      </select>
                      {!newItem.pageId && (
                        <p className="text-xs text-red-500 mt-1">Please select a page target</p>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Button Style</label>
                    <select
                      value={newItem.buttonStyle}
                      onChange={(e) => setNewItem({ ...newItem, buttonStyle: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    >
                      <option value="primary">Primary</option>
                      <option value="secondary">Secondary</option>
                      <option value="outline">Outline</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">External URL (optional)</label>
                    <input
                      type="url"
                      value={newItem.externalUrl}
                      onChange={(e) => setNewItem({ ...newItem, externalUrl: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="https://example.com"
                    />
                    <p className="text-xs text-gray-500 mt-1">If provided, button will link to this URL</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Button Action (optional)</label>
                    <input
                      type="text"
                      value={newItem.buttonAction}
                      onChange={(e) => setNewItem({ ...newItem, buttonAction: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="onClick handler name"
                    />
                    <p className="text-xs text-gray-500 mt-1">JavaScript function name to call on click</p>
                  </div>
                </>
              )}

              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newItem.enabled}
                    onChange={(e) => setNewItem({ ...newItem, enabled: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm font-medium">Enabled</span>
                </label>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleAddItem}
                disabled={
                  saving ||
                  !newItem.label ||
                  (newItem.type === 'LINK' && !newItem.isRoot && !newItem.pageId)
                }
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {saving ? 'Adding...' : 'Add Item'}
              </button>
              <button
                onClick={() => {
                  setShowAddModal(false)
                  setNewItem({ label: '', type: 'LINK', isRoot: false, pageId: '', enabled: true, buttonStyle: 'primary', buttonAction: '', externalUrl: '' })
                }}
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Dialog */}
      <ConfirmDialog
        open={showDeleteDialog !== null}
        onOpenChange={(open) => setShowDeleteDialog(open ? showDeleteDialog : null)}
        title="Delete Menu Item"
        description="Are you sure you want to delete this menu item? This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={async () => {
          if (showDeleteDialog) {
            await handleDeleteItem(showDeleteDialog)
          }
        }}
        destructive
      />

      {/* Translate Modal */}
      {showTranslateModal && menu && (
        <TranslateModal
          open={showTranslateModal !== null}
          onOpenChange={(open) => setShowTranslateModal(open ? showTranslateModal : null)}
          sourceLocale={defaultLocale}
          hasGlossary={false}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch('/api/admin/translate/menu-item', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                menuItemId: showTranslateModal,
                sourceLocale,
                targetLocales,
                mode,
              }),
            })

            if (!response.ok) {
              const error = await response.json()
              throw new Error(error.error || 'Translation failed')
            }

            const data = await response.json()
            
            // Refresh i18n for this item
            await fetchMenuItemI18n(showTranslateModal)
            
            return data
          }}
        />
      )}

      {showMenuTranslateModal && menu && (
        <TranslateModal
          open={showMenuTranslateModal}
          onOpenChange={setShowMenuTranslateModal}
          sourceLocale={defaultLocale}
          hasGlossary={false}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch('/api/admin/translate/menu', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                menuId: menu.id,
                sourceLocale,
                targetLocales,
                mode,
              }),
            })

            if (!response.ok) {
              const error = await response.json()
              throw new Error(error.error || 'Translation failed')
            }

            const data = await response.json()
            
            // Refresh i18n for menu
            await fetchMenuI18n()
            
            return data
          }}
        />
      )}
    </div>
  )
}
