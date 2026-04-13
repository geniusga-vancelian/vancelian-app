'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { PlusCircle } from 'lucide-react'
import { CreatePageModal } from '@/components/admin/CreatePageModal'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'
import { ChevronDown, ChevronUp, ChevronLeft, ChevronRight } from 'lucide-react'

interface Page {
  id: string
  slug: string
  urlPath: string
  title: string | null
  template: string
  description: string | null
  createdAt: string
  sections: Array<{
    id: string
    key: string
    order: number
  }>
}

interface MenuPage {
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
  page: MenuPage | null
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

export default function AdminPagesPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'menus' | 'pages'>('menus')
  
  // Pages state
  const [pages, setPages] = useState<Page[]>([])
  const [pagesLoading, setPagesLoading] = useState(true)
  const [pagesError, setPagesError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [showDeletePageDialog, setShowDeletePageDialog] = useState<string | null>(null)
  const [deletingPage, setDeletingPage] = useState(false)
  
  // Menu state
  const [menu, setMenu] = useState<Menu | null>(null)
  const [menuPages, setMenuPages] = useState<MenuPage[]>([])
  const [menuLoading, setMenuLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [menuName, setMenuName] = useState('')
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState<string | null>(null)
  const [expandedI18nItems, setExpandedI18nItems] = useState<Set<string>>(new Set())
  const [expandedMenuI18n, setExpandedMenuI18n] = useState(false)
  const [i18nLabels, setI18nLabels] = useState<Record<string, Record<string, string>>>({})
  const [i18nStatuses, setI18nStatuses] = useState<Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>>>({})
  const [menuI18nNames, setMenuI18nNames] = useState<Record<string, string>>({})
  const [menuI18nStatuses, setMenuI18nStatuses] = useState<Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>>({})
  const [showTranslateModal, setShowTranslateModal] = useState<string | null>(null)
  const [showMenuTranslateModal, setShowMenuTranslateModal] = useState(false)
  const [savingI18n, setSavingI18n] = useState<Record<string, boolean>>({})
  const [savingMenuI18n, setSavingMenuI18n] = useState(false)
  const [approving, setApproving] = useState<Record<string, string>>({})
  const [approvingMenu, setApprovingMenu] = useState<string>('')
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
    fetchMenu()
    fetchMenuPages()
  }, [])

  // Pages functions
  const fetchPages = async () => {
    setPagesLoading(true)
    setPagesError(null)
    try {
      const res = await fetch('/api/admin/pages')
      const data = await res.json()
      if (data.pages) {
        setPages(data.pages)
      } else if (data.error === 'Unauthorized') {
        router.push('/admin/login')
      }
    } catch (e: any) {
      setPagesError(e.message || 'Failed to load pages')
    } finally {
      setPagesLoading(false)
    }
  }

  const handleCreateHomePage = async () => {
    setCreating(true)
    setPagesError(null)
    try {
      const response = await fetch('/api/admin/pages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug: 'home', template: 'homepage', title: 'Homepage' }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create home page')
      }

      await fetchPages()
    } catch (e: any) {
      setPagesError(e.message || 'Failed to create home page')
    } finally {
      setCreating(false)
    }
  }

  const handleDeletePage = async (slug: string) => {
    setDeletingPage(true)
    try {
      const response = await fetch(`/api/admin/pages/${slug}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete page')
      }

      toastSuccess('Page deleted successfully')
      await fetchPages()
      setShowDeletePageDialog(null)
    } catch (e: any) {
      toastError(e.message || 'Failed to delete page')
    } finally {
      setDeletingPage(false)
    }
  }

  // Menu functions
  const fetchMenuPages = async () => {
    try {
      const response = await fetch('/api/admin/pages')
      if (!response.ok) {
        throw new Error('Failed to fetch pages')
      }
      const data = await response.json()
      setMenuPages(data.pages || [])
    } catch (error) {
      console.error('Error fetching pages:', error)
    }
  }

  const fetchMenu = async () => {
    try {
      const response = await fetch('/api/admin/menus/primary?locale=fr')
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch menu')
      }

      const data = await response.json()
      setMenu(data.menu)
      setMenuName(data.menu.nameBase || data.menu.name)
      
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
      setMenuLoading(false)
    }
  }

  const fetchMenuItemI18n = async (itemId: string) => {
    try {
      const response = await fetch(`/api/admin/menu-items/${itemId}/i18n`)
      if (!response.ok) {
        throw new Error('Failed to fetch i18n')
      }
      const data = await response.json()
      
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
        fetchMenuItemI18n(itemId)
      }
      return newSet
    })
  }

  const fetchMenuI18n = async () => {
    if (!menu) return
    try {
      const response = await fetch(`/api/admin/menus/${menu.id}/i18n`)
      if (!response.ok) {
        throw new Error('Failed to fetch menu i18n')
      }
      const data = await response.json()
      
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
      const response = await fetch(`/api/admin/menus/${menu.id}/i18n`, {
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
      throw error
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

  const toggleMenuI18nExpanded = () => {
    if (!expandedMenuI18n && menu) {
      fetchMenuI18n()
    }
    setExpandedMenuI18n(!expandedMenuI18n)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Menu & Pages</h1>
        <Link
          href="/admin"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to Dashboard
        </Link>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('menus')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'menus'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Menus
          </button>
          <button
            onClick={() => setActiveTab('pages')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'pages'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Pages
          </button>
        </nav>
      </div>

      {/* Menus Section */}
      {activeTab === 'menus' && (
        <div className="space-y-6">
          {menuLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500">Loading menu...</div>
            </div>
          ) : !menu ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500">Menu not found.</div>
            </div>
          ) : (
            <>
              {/* Menu Name */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold mb-4">Primary Menu</h2>
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Menu Name</label>
                    <input
                      type="text"
                      value={menuName}
                      onChange={(e) => setMenuName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                  <button
                    onClick={handleSaveMenuName}
                    disabled={saving}
                    className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save Name'}
                  </button>
                </div>

                {/* Menu Name Localization */}
                <div className="mt-4">
                  <button
                    onClick={toggleMenuI18nExpanded}
                    className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
                  >
                    {expandedMenuI18n ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    Localized Names
                  </button>
                  {expandedMenuI18n && (
                    <div className="mt-3 space-y-3 pl-6 border-l-2 border-gray-200">
                      {supportedLocales.map((locale) => (
                        <div key={locale} className="flex items-center gap-3">
                          <div className="flex-1">
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              {locale.toUpperCase()}
                            </label>
                            <input
                              type="text"
                              value={menuI18nNames[locale] || ''}
                              onChange={(e) =>
                                setMenuI18nNames((prev) => ({ ...prev, [locale]: e.target.value }))
                              }
                              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                            />
                          </div>
                          {menuI18nStatuses[locale] && (
                            <span
                              className={`px-2 py-1 text-xs rounded ${
                                menuI18nStatuses[locale] === 'APPROVED'
                                  ? 'bg-green-100 text-green-800'
                                  : menuI18nStatuses[locale] === 'MACHINE'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {menuI18nStatuses[locale]}
                            </span>
                          )}
                          <button
                            onClick={() => handleSaveMenuI18nName(locale)}
                            disabled={savingMenuI18n}
                            className="px-3 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setShowMenuTranslateModal(true)}
                            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                          >
                            Auto-translate
                          </button>
                          {menuI18nStatuses[locale] === 'MACHINE' && (
                            <button
                              onClick={() => handleApproveMenuTranslation(locale)}
                              disabled={approvingMenu === locale}
                              className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                            >
                              {approvingMenu === locale ? 'Approving...' : 'Approve'}
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Menu Items */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-semibold">Menu Items</h2>
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
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
                                <div className="flex items-center gap-1">
                                  <button
                                    onClick={() => handleMoveUp(index)}
                                    disabled={index === 0 || saving}
                                    className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                                  >
                                    <ChevronUp className="w-4 h-4" />
                                  </button>
                                  <span className="text-sm text-gray-600">{item.order}</span>
                                  <button
                                    onClick={() => handleMoveDown(index)}
                                    disabled={index === menu.items.length - 1 || saving}
                                    className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                                  >
                                    <ChevronDown className="w-4 h-4" />
                                  </button>
                                </div>
                              </td>
                              <td className="py-3 px-4">
                                <span className="text-sm text-gray-700">{item.type}</span>
                              </td>
                              <td className="py-3 px-4">
                                {editingItem?.id === item.id ? (
                                  <input
                                    type="text"
                                    value={item.label}
                                    onChange={(e) =>
                                      setEditingItem({ ...editingItem, label: e.target.value })
                                    }
                                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500"
                                    onBlur={() => handleUpdateItem(editingItem)}
                                    autoFocus
                                  />
                                ) : (
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm text-gray-900">{item.label}</span>
                                    {item.isInvalidTarget && (
                                      <span className="px-2 py-0.5 text-xs bg-red-100 text-red-800 rounded">
                                        Invalid target
                                      </span>
                                    )}
                                  </div>
                                )}
                              </td>
                              <td className="py-3 px-4">
                                {editingItem?.id === item.id ? (
                                  item.type === 'BUTTON' ? (
                                    <div className="space-y-2">
                                      <input
                                        type="text"
                                        placeholder="External URL"
                                        value={item.externalUrl || ''}
                                        onChange={(e) =>
                                          setEditingItem({ ...editingItem, externalUrl: e.target.value })
                                        }
                                        className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                                      />
                                      <select
                                        value={item.buttonStyle || 'primary'}
                                        onChange={(e) =>
                                          setEditingItem({ ...editingItem, buttonStyle: e.target.value })
                                        }
                                        className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                                      >
                                        <option value="primary">Primary</option>
                                        <option value="secondary">Secondary</option>
                                        <option value="outline">Outline</option>
                                      </select>
                                    </div>
                                  ) : (
                                    <div className="space-y-2">
                                      <label className="flex items-center gap-2">
                                        <input
                                          type="checkbox"
                                          checked={item.isRoot}
                                          onChange={(e) =>
                                            setEditingItem({ ...editingItem, isRoot: e.target.checked, pageId: null })
                                          }
                                          className="rounded"
                                        />
                                        <span className="text-xs">Use site root (/)</span>
                                      </label>
                                      {!item.isRoot && (
                                        <select
                                          value={item.pageId || ''}
                                          onChange={(e) =>
                                            setEditingItem({ ...editingItem, pageId: e.target.value })
                                          }
                                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                                        >
                                          <option value="">Select Page target</option>
                                          {menuPages.map((page) => (
                                            <option key={page.id} value={page.id}>
                                              {page.title || page.slug} — {page.computedUrlPath}
                                            </option>
                                          ))}
                                        </select>
                                      )}
                                    </div>
                                  )
                                ) : (
                                  <span className="text-sm text-gray-600">
                                    {item.type === 'BUTTON'
                                      ? item.externalUrl || '—'
                                      : item.isRoot
                                      ? 'Use site root (/)'
                                      : item.page
                                      ? `${item.page.title || item.page.slug} — ${item.page.computedUrlPath}`
                                      : '—'}
                                  </span>
                                )}
                              </td>
                              <td className="py-3 px-4">
                                <span className="text-sm text-gray-500 font-mono">
                                  {item.computedUrlPath || '—'}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                {editingItem?.id === item.id ? (
                                  <label className="flex items-center gap-2">
                                    <input
                                      type="checkbox"
                                      checked={item.enabled}
                                      onChange={(e) =>
                                        setEditingItem({ ...editingItem, enabled: e.target.checked })
                                      }
                                      className="rounded"
                                    />
                                    <span className="text-xs">Enabled</span>
                                  </label>
                                ) : (
                                  <span
                                    className={`px-2 py-1 text-xs rounded ${
                                      item.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                    }`}
                                  >
                                    {item.enabled ? 'Yes' : 'No'}
                                  </span>
                                )}
                              </td>
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2">
                                  {editingItem?.id === item.id ? (
                                    <>
                                      <button
                                        onClick={() => handleUpdateItem(editingItem)}
                                        disabled={saving}
                                        className="px-3 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                                      >
                                        Save
                                      </button>
                                      <button
                                        onClick={() => setEditingItem(null)}
                                        className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                      >
                                        Cancel
                                      </button>
                                    </>
                                  ) : (
                                    <>
                                      <button
                                        onClick={() => setEditingItem(item)}
                                        className="px-3 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
                                      >
                                        Edit
                                      </button>
                                      <button
                                        onClick={() => setShowDeleteDialog(item.id)}
                                        className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                                      >
                                        Delete
                                      </button>
                                    </>
                                  )}
                                </div>
                              </td>
                            </tr>
                            {expandedI18nItems.has(item.id) && (
                              <tr key={`${item.id}-i18n`}>
                                <td colSpan={7} className="px-4 py-3 bg-gray-50">
                                  <div className="space-y-3">
                                    <h4 className="text-sm font-medium text-gray-700 mb-2">Localized Labels</h4>
                                    {supportedLocales.map((locale) => (
                                      <div key={locale} className="flex items-center gap-3">
                                        <div className="flex-1">
                                          <label className="block text-xs font-medium text-gray-600 mb-1">
                                            {locale.toUpperCase()}
                                          </label>
                                          <input
                                            type="text"
                                            value={i18nLabels[item.id]?.[locale] || ''}
                                            onChange={(e) =>
                                              setI18nLabels((prev) => ({
                                                ...prev,
                                                [item.id]: { ...prev[item.id], [locale]: e.target.value },
                                              }))
                                            }
                                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                          />
                                        </div>
                                        {i18nStatuses[item.id]?.[locale] && (
                                          <span
                                            className={`px-2 py-1 text-xs rounded ${
                                              i18nStatuses[item.id][locale] === 'APPROVED'
                                                ? 'bg-green-100 text-green-800'
                                                : i18nStatuses[item.id][locale] === 'MACHINE'
                                                ? 'bg-yellow-100 text-yellow-800'
                                                : 'bg-gray-100 text-gray-800'
                                            }`}
                                          >
                                            {i18nStatuses[item.id][locale]}
                                          </span>
                                        )}
                                        <button
                                          onClick={() => handleSaveI18nLabel(item.id, locale)}
                                          disabled={savingI18n[item.id]}
                                          className="px-3 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                                        >
                                          Save
                                        </button>
                                        <button
                                          onClick={() => setShowTranslateModal(item.id)}
                                          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                                        >
                                          Auto-translate
                                        </button>
                                        {i18nStatuses[item.id]?.[locale] === 'MACHINE' && (
                                          <button
                                            onClick={() => handleApproveTranslation(item.id, locale)}
                                            disabled={approving[`${item.id}:${locale}`] === 'true'}
                                            className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                                          >
                                            {approving[`${item.id}:${locale}`] === 'true' ? 'Approving...' : 'Approve'}
                                          </button>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </td>
                              </tr>
                            )}
                            <tr key={`${item.id}-toggle`}>
                              <td colSpan={7} className="px-4 py-2 bg-gray-50">
                                <button
                                  onClick={() => toggleI18nExpanded(item.id)}
                                  className="flex items-center gap-2 text-xs text-gray-600 hover:text-gray-900"
                                >
                                  {expandedI18nItems.has(item.id) ? (
                                    <>
                                      <ChevronUp className="w-3 h-3" />
                                      Hide localized labels
                                    </>
                                  ) : (
                                    <>
                                      <ChevronDown className="w-3 h-3" />
                                      Show localized labels
                                    </>
                                  )}
                                </button>
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
            </>
          )}
        </div>
      )}

      {/* Pages Section */}
      {activeTab === 'pages' && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <Button onClick={() => setIsCreateModalOpen(true)}>
              <PlusCircle className="w-4 h-4 mr-2" />
              Add a page
            </Button>
          </div>

          {pagesLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500">Loading...</div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Title
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Slug
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      URL
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Template
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Sections
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {pages.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-4 text-center">
                        <div className="flex flex-col items-center gap-3">
                          <p className="text-gray-500">No pages found. Create your first page!</p>
                          <button
                            onClick={handleCreateHomePage}
                            disabled={creating}
                            className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {creating ? 'Creating...' : 'Create Home Page'}
                          </button>
                          <p className="text-xs text-gray-400 max-w-md">
                            This will create the "home" page with standard sections (hero, features, projects, pricing, footer)
                          </p>
                          {pagesError && (
                            <p className="text-xs text-red-600">{pagesError}</p>
                          )}
                        </div>
                      </td>
                    </tr>
                  ) : (
                    pages.map((page) => (
                      <tr key={page.id}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            {page.title || page.slug}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500 font-mono">
                            {page.slug}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500 font-mono">
                            {page.urlPath}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">
                            {page.template}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">
                            {page.sections.length} section(s)
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex items-center justify-end gap-3">
                            <Link
                              href={`/admin/pages/${page.slug}`}
                              className="text-indigo-600 hover:text-indigo-900"
                            >
                              Edit
                            </Link>
                            <button
                              onClick={() => setShowDeletePageDialog(page.slug)}
                              className="text-red-600 hover:text-red-900"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Add Menu Item Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Add Menu Item</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Label</label>
                <input
                  type="text"
                  value={newItem.label}
                  onChange={(e) => setNewItem({ ...newItem, label: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      value="LINK"
                      checked={newItem.type === 'LINK'}
                      onChange={(e) => setNewItem({ ...newItem, type: e.target.value as 'LINK' | 'BUTTON' })}
                    />
                    <span>Link</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      value="BUTTON"
                      checked={newItem.type === 'BUTTON'}
                      onChange={(e) => setNewItem({ ...newItem, type: e.target.value as 'LINK' | 'BUTTON' })}
                    />
                    <span>Button</span>
                  </label>
                </div>
              </div>
              {newItem.type === 'BUTTON' ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">External URL</label>
                    <input
                      type="text"
                      value={newItem.externalUrl}
                      onChange={(e) => setNewItem({ ...newItem, externalUrl: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                      placeholder="https://..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Button Style</label>
                    <select
                      value={newItem.buttonStyle}
                      onChange={(e) => setNewItem({ ...newItem, buttonStyle: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="primary">Primary</option>
                      <option value="secondary">Secondary</option>
                      <option value="outline">Outline</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Button Action (optional)</label>
                    <input
                      type="text"
                      value={newItem.buttonAction}
                      onChange={(e) => setNewItem({ ...newItem, buttonAction: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                      placeholder="functionName"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={newItem.isRoot}
                        onChange={(e) => setNewItem({ ...newItem, isRoot: e.target.checked, pageId: '' })}
                        className="rounded"
                      />
                      <span className="text-sm">Use site root (/)</span>
                    </label>
                  </div>
                  {!newItem.isRoot && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Page target</label>
                      <select
                        value={newItem.pageId}
                        onChange={(e) => setNewItem({ ...newItem, pageId: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="">Select Page target</option>
                        {menuPages.map((page) => (
                          <option key={page.id} value={page.id}>
                            {page.title || page.slug} — {page.computedUrlPath}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
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
                  <span className="text-sm">Enabled</span>
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowAddModal(false)
                  setNewItem({ label: '', type: 'LINK', isRoot: false, pageId: '', enabled: true, buttonStyle: 'primary', buttonAction: '', externalUrl: '' })
                }}
                className="px-4 py-2 text-sm bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleAddItem}
                disabled={saving}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {saving ? 'Adding...' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      <ConfirmDialog
        open={showDeleteDialog !== null}
        onOpenChange={(open) => setShowDeleteDialog(open ? showDeleteDialog : null)}
        onConfirm={async () => {
          if (showDeleteDialog) {
            await handleDeleteItem(showDeleteDialog)
            setShowDeleteDialog(null)
          }
        }}
        title="Delete Menu Item"
        description="Cette action supprime un élément de menu et sera irréversible si vous la validez."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        destructive
      />

      {showTranslateModal && (
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
            await fetchMenuItemI18n(showTranslateModal)
            await fetchMenu()
            
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
            await fetchMenuI18n()
            await fetchMenu()
            
            return data
          }}
        />
      )}

      <CreatePageModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={fetchPages}
      />

      {/* Delete Page Confirmation Dialog */}
      <ConfirmDialog
        open={showDeletePageDialog !== null}
        onOpenChange={(open) => setShowDeletePageDialog(open ? showDeletePageDialog : null)}
        onConfirm={async () => {
          if (showDeletePageDialog) {
            await handleDeletePage(showDeletePageDialog)
          }
        }}
        title="Delete Page"
        description="Cette action supprime une page et toutes ses sections. Cette action est irréversible si vous la validez. Les éléments de menu qui pointent vers cette page seront désactivés."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        destructive
      />
    </div>
  )
}
