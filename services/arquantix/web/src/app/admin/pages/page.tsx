'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { CreatePageModal } from '@/components/admin/CreatePageModal'
import { AddPrimaryNavButtonDialog } from '@/components/admin/AddPrimaryNavButtonDialog'
import { SiteStructureTree } from '@/components/admin/SiteStructureTree'
import { CreateCommonModuleModal } from '@/components/admin/CreateCommonModuleModal'
import { SiteAdminHealthBar } from '@/components/admin/SiteAdminHealthBar'
import { useAdminEditingLocale } from '@/components/admin/AdminEditingLocaleContext'
import type {
  SiteTreeGlobalCommonModuleRow,
  SiteTreeNavRightRailRow,
  SiteTreeNode,
} from '@/lib/cms/buildSiteTree'
import { defaultLocale, type Locale } from '@/config/locales'
import { computeMenuEditorPolicy } from '@/lib/admin/menuEditorPolicy'

export default function AdminPagesPage() {
  const router = useRouter()
  const { locale: editingLocale } = useAdminEditingLocale()
  const menuPolicy = computeMenuEditorPolicy(editingLocale, defaultLocale as Locale)
  const isMenuStructureLocked = menuPolicy.isStructureLocked

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [siteTree, setSiteTree] = useState<SiteTreeNode[] | null>(null)
  const [siteTreeLoading, setSiteTreeLoading] = useState(false)
  const [siteTreeError, setSiteTreeError] = useState<string | null>(null)
  const [addNavButtonModalOpen, setAddNavButtonModalOpen] = useState(false)
  const [navRightRail, setNavRightRail] = useState<SiteTreeNavRightRailRow[]>([])
  const [globalCommonModules, setGlobalCommonModules] = useState<SiteTreeGlobalCommonModuleRow[]>([])
  const [previewReloadEpoch, setPreviewReloadEpoch] = useState(0)
  const [commonModuleModalOpen, setCommonModuleModalOpen] = useState(false)

  const refreshSiteTree = useCallback(async () => {
    setSiteTreeLoading(true)
    setSiteTreeError(null)
    try {
      const res = await fetch(
        `/api/admin/site-tree?locale=${encodeURIComponent(editingLocale)}`,
      )
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || res.statusText || 'Erreur site-tree')
      }
      setSiteTree(Array.isArray(data.tree) ? data.tree : [])
      setNavRightRail(Array.isArray(data.navRightRail) ? data.navRightRail : [])
      setGlobalCommonModules(
        Array.isArray(data.globalCommonModules) ? data.globalCommonModules : [],
      )
      setPreviewReloadEpoch((n) => n + 1)
    } catch (e: unknown) {
      setSiteTreeError(e instanceof Error ? e.message : 'Erreur')
      setSiteTree(null)
      setNavRightRail([])
      setGlobalCommonModules([])
    } finally {
      setSiteTreeLoading(false)
    }
  }, [editingLocale])

  useEffect(() => {
    void refreshSiteTree()
  }, [editingLocale, refreshSiteTree])

  const openMenusEditor = () => {
    router.push('/admin/pages/menu')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Pages</h1>
        <Link
          href="/admin"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to Dashboard
        </Link>
      </div>

      <div className="space-y-6">
        <SiteAdminHealthBar active onOpenMenusTab={openMenusEditor} />
        <SiteStructureTree
          tree={siteTree}
          locale={editingLocale}
          loading={siteTreeLoading}
          error={siteTreeError}
          onRefresh={refreshSiteTree}
          onNavigateToMenus={openMenusEditor}
          onAddPage={() => setIsCreateModalOpen(true)}
          onAddNavButton={
            isMenuStructureLocked ? undefined : () => setAddNavButtonModalOpen(true)
          }
          navRightRail={navRightRail}
          globalCommonModules={globalCommonModules}
          onAddCommonModule={
            isMenuStructureLocked ? undefined : () => setCommonModuleModalOpen(true)
          }
          readOnlyStructure={isMenuStructureLocked}
          previewReloadEpoch={previewReloadEpoch}
          autoOpenFirstPreviewOnLoad
        />
        <AddPrimaryNavButtonDialog
          open={addNavButtonModalOpen}
          onOpenChange={setAddNavButtonModalOpen}
          readOnly={isMenuStructureLocked}
          onCreated={refreshSiteTree}
        />
      </div>

      <CreatePageModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={async () => {
          await refreshSiteTree()
        }}
        siteTree={siteTree}
        siteTreeLoading={siteTreeLoading}
      />
      <CreateCommonModuleModal
        open={commonModuleModalOpen}
        onClose={() => setCommonModuleModalOpen(false)}
        onCreated={async () => {
          await refreshSiteTree()
        }}
      />
    </div>
  )
}
