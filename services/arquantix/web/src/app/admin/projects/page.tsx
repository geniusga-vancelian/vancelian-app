'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, Search, Edit } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ContentStatus } from '@prisma/client'
import { toastError } from '@/lib/admin/toast'
import { adminMediaFileUrl } from '@/lib/admin/adminMediaFileUrl'

interface Project {
  id: string
  slug: string
  status: ContentStatus
  updatedAt: string
  coverMedia: {
    id: string
    url: string
  } | null
  i18n: Array<{
    title: string
    locale: string
  }>
}

export default function AdminProjectsPage() {
  const router = useRouter()
  const blockNewProjectsUi = process.env.NEXT_PUBLIC_ADMIN_BLOCK_PROJECT_BASED_EO === 'true'
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<ContentStatus | 'ALL'>('ALL')

  const fetchProjects = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (searchQuery) params.set('query', searchQuery)
      if (statusFilter !== 'ALL') params.set('status', statusFilter)

      const response = await fetch(`/api/admin/projects?${params.toString()}`)
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch projects')
      }

      const data = await response.json()
      setProjects(data.projects || [])
    } catch (error) {
      console.error('Error fetching projects:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [searchQuery, statusFilter, router])

  const handleCreateProject = async () => {
    try {
      const response = await fetch('/api/admin/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slug: `project-${Date.now()}`,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        const msg =
          typeof error?.detail === 'string'
            ? error.detail
            : error.error || 'Failed to create project'
        throw new Error(msg)
      }

      const data = await response.json()
      router.push(`/admin/projects/${data.project.id}`)
    } catch (error: any) {
      toastError(error.message || 'Failed to create project')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading projects...</div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Projects (legacy CMS)</h1>
        <Button onClick={handleCreateProject} disabled={blockNewProjectsUi}>
          <Plus className="w-4 h-4 mr-2" />
          New Project
        </Button>
      </div>

      <div className="mb-6 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
        <p className="font-medium">Exclusive Offers — point d’entrée admin canonique</p>
        <p className="mt-1 text-sky-900/90">
          Les offres exclusives se gèrent dans{' '}
          <Link href="/admin/vault-builder/exclusive-offers" className="font-semibold underline hover:text-sky-950">
            Vault Builder · Exclusive Offers
          </Link>{' '}
          (page + <code className="text-xs bg-sky-100/80 px-1 rounded">packaged_products</code> + moteur lending). Cette section Projects reste utile pour le
          legacy CMS, articles et contenus non migrés — pas comme source catalogue EO.
        </p>
      </div>

      {blockNewProjectsUi && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p className="font-medium">Exclusive Offers — création désactivée depuis Projects</p>
          <p className="mt-1 text-amber-900/90">
            Créez le contenu produit dans <strong>Vault Builder</strong> et le registre{' '}
            <strong>Packaged Product</strong>. Les projets CMS restent disponibles pour édition
            legacy / articles liés. Rollback serveur : <code className="rounded bg-amber-100/80 px-1">ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO=true</code>
          </p>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-center">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as ContentStatus | 'ALL')}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="ALL">All Status</option>
            <option value="DRAFT">Draft</option>
            <option value="PUBLISHED">Published</option>
          </select>
        </div>
      </div>

      {/* Projects Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cover
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Title
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Slug
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Updated
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {projects.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                  No projects found. Create your first project!
                </td>
              </tr>
            ) : (
              projects.map((project) => {
                const title = project.i18n[0]?.title || project.slug
                return (
                  <tr key={project.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {project.coverMedia ? (
                        <img
                          src={adminMediaFileUrl(project.coverMedia.id)}
                          alt={title}
                          className="w-16 h-16 object-cover rounded"
                        />
                      ) : (
                        <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center text-gray-400 text-xs">
                          No cover
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{title}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{project.slug}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          project.status === 'PUBLISHED'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {project.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(project.updatedAt).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <Link
                        href={`/admin/projects/${project.id}`}
                        className="text-indigo-600 hover:text-indigo-900 flex items-center justify-end"
                      >
                        <Edit className="w-4 h-4 mr-1" /> Edit
                      </Link>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

