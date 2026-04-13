'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Plus, Trash2, Copy, ArrowUp, ArrowDown } from 'lucide-react'
import { PageSettings } from '@/components/admin/PageSettings'
import { SectionLibraryModal } from '@/components/admin/SectionLibraryModal'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'

interface Section {
  id: string
  key: string
  order: number
  schemaVersion: string
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
}

export default function AdminPageSectionsPage() {
  const router = useRouter()
  const params = useParams()
  const slug = (params?.slug as string | undefined) ?? ''

  const [page, setPage] = useState<Page | null>(null)
  const [sections, setSections] = useState<Section[]>([])
  const [loading, setLoading] = useState(true)
  const [isLibraryModalOpen, setIsLibraryModalOpen] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [sectionToDelete, setSectionToDelete] = useState<string | null>(null)

  const fetchPageData = async () => {
    if (!slug) return

    try {
      // Fetch page details
      const pageRes = await fetch(`/api/admin/pages/${slug}`)
      if (!pageRes.ok) {
        if (pageRes.status === 401) {
          router.push('/admin/login')
          return
        }
        if (pageRes.status === 404) {
          router.push('/admin/pages')
          return
        }
        throw new Error('Failed to fetch page')
      }
      const pageData = await pageRes.json()
      setPage(pageData.page)

      // Fetch sections
      const sectionsRes = await fetch(`/api/admin/pages/${slug}/sections`)
      if (!sectionsRes.ok) {
        throw new Error('Failed to fetch sections')
      }
      const sectionsData = await sectionsRes.json()
      setSections(sectionsData.sections || [])
    } catch (error) {
      console.error('Error fetching page data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPageData()
  }, [slug, router])

  const handleAddSection = async (typeKey: string) => {
    setIsProcessing(true)
    try {
      const response = await fetch(`/api/admin/pages/${slug}/sections/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ typeKey }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to add section')
      }

      toastSuccess('Section added')
      await fetchPageData()
    } catch (error: any) {
      toastError(error.message || 'Failed to add section')
    } finally {
      setIsProcessing(false)
    }
  }

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

  const handleDuplicateSection = async (sectionId: string) => {
    setIsProcessing(true)
    try {
      const response = await fetch(`/api/admin/sections/${sectionId}/duplicate`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to duplicate section')
      }

      toastSuccess('Section duplicated')
      await fetchPageData()
    } catch (error: any) {
      toastError(error.message || 'Failed to duplicate section')
    } finally {
      setIsProcessing(false)
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!page) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Page not found.</div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {page.title || slug}
          </h1>
        </div>
        <Link
          href="/admin/pages"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to Pages
        </Link>
      </div>

      {/* Page Settings */}
      <PageSettings page={page} onUpdate={fetchPageData} />

      {/* Sections */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Sections</h2>
        <Button onClick={() => setIsLibraryModalOpen(true)} disabled={isProcessing}>
          <Plus className="w-4 h-4 mr-2" />
          Add Section
        </Button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Order
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Key
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Schema Version
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Contents
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sections.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  No sections found for this page.
                </td>
              </tr>
            ) : (
              sections.map((section) => (
                <tr key={section.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {section.order}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {section.key}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {section.schemaVersion}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {section.contents.length} content(s)
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleMoveSection(section.id, 'up')}
                        disabled={isProcessing || sections.findIndex((s) => s.id === section.id) === 0}
                        className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Move up"
                      >
                        <ArrowUp className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleMoveSection(section.id, 'down')}
                        disabled={isProcessing || sections.findIndex((s) => s.id === section.id) === sections.length - 1}
                        className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Move down"
                      >
                        <ArrowDown className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDuplicateSection(section.id)}
                        disabled={isProcessing}
                        className="p-1 text-gray-400 hover:text-blue-600 disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Duplicate"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteClick(section.id)}
                        disabled={isProcessing}
                        className="p-1 text-gray-400 hover:text-red-600 disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <Link
                        href={`/admin/sections/${section.id}`}
                        className="text-indigo-600 hover:text-indigo-900 px-2 py-1"
                      >
                        Edit
                      </Link>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <SectionLibraryModal
        isOpen={isLibraryModalOpen}
        onClose={() => setIsLibraryModalOpen(false)}
        onSelect={handleAddSection}
        pageTemplate={page?.template || 'homepage'}
      />

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
    </div>
  )
}

