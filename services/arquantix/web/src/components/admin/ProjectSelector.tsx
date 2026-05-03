'use client'

import { useState, useEffect } from 'react'
import { X, Search, GripVertical } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ContentStatus } from '@prisma/client'
import { adminMediaFileUrl } from '@/lib/admin/adminMediaFileUrl'

interface Project {
  id: string
  slug: string
  status: ContentStatus
  coverMedia: {
    id: string
    url: string
  } | null
  i18n: Array<{
    title: string
    locale: string
  }>
}

interface ProjectSelectorProps {
  selectedProjectIds: string[]
  onChange: (projectIds: string[]) => void
  limit?: number
}

export function ProjectSelector({
  selectedProjectIds,
  onChange,
  limit = 3,
}: ProjectSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)

  // Fetch selected projects by their IDs
  const fetchSelectedProjects = async () => {
    try {
      // Fetch all published projects and filter by selected IDs
      const params = new URLSearchParams()
      params.set('status', 'PUBLISHED')
      params.set('pageSize', '100') // Get enough projects to find our selected ones

      const response = await fetch(`/api/admin/projects?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to fetch projects')
      }

      const data = await response.json()
      const allProjects = data.projects || []
      
      // Filter to only selected projects
      const selected = allProjects.filter((p: Project) =>
        selectedProjectIds.includes(p.id)
      )
      
      // Merge with existing projects (avoid duplicates)
      setProjects((prev) => {
        const existingIds = prev.map((p) => p.id)
        const newProjects = selected.filter(
          (p: Project) => !existingIds.includes(p.id)
        )
        return newProjects.length > 0 ? [...prev, ...newProjects] : prev
      })
    } catch (error) {
      console.error('Error fetching selected projects:', error)
    }
  }

  // Load selected projects when selectedProjectIds changes
  useEffect(() => {
    if (selectedProjectIds.length === 0) return

    // Check if we need to fetch any projects
    const existingIds = projects.map((p) => p.id)
    const missingIds = selectedProjectIds.filter((id) => !existingIds.includes(id))
    
    // If there are missing projects, fetch them
    if (missingIds.length > 0) {
      fetchSelectedProjects()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectIds.join(',')]) // Re-run when selectedProjectIds changes

  useEffect(() => {
    if (isOpen) {
      fetchProjects()
    }
  }, [isOpen, searchQuery])

  const fetchProjects = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('status', 'PUBLISHED')
      if (searchQuery) {
        params.set('query', searchQuery)
      }

      const response = await fetch(`/api/admin/projects?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to fetch projects')
      }

      const data = await response.json()
      const fetchedProjects = data.projects || []
      
      // Merge with existing projects (avoid duplicates)
      setProjects((prev) => {
        const existingIds = prev.map((p) => p.id)
        const newProjects = fetchedProjects.filter(
          (p: Project) => !existingIds.includes(p.id)
        )
        return [...prev, ...newProjects]
      })
    } catch (error) {
      console.error('Error fetching projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectProject = (projectId: string) => {
    if (selectedProjectIds.includes(projectId)) {
      // Already selected, remove it
      onChange(selectedProjectIds.filter((id) => id !== projectId))
    } else {
      // Add to selection (respect limit)
      if (selectedProjectIds.length < limit) {
        onChange([...selectedProjectIds, projectId])
      }
    }
  }

  const handleRemoveProject = (projectId: string) => {
    onChange(selectedProjectIds.filter((id) => id !== projectId))
  }

  const handleMoveProject = (fromIndex: number, toIndex: number) => {
    const newOrder = [...selectedProjectIds]
    const [moved] = newOrder.splice(fromIndex, 1)
    newOrder.splice(toIndex, 0, moved)
    onChange(newOrder)
  }

  // Get selected projects with their data
  const selectedProjects = projects.filter((p) => selectedProjectIds.includes(p.id))
  // Sort by selectedProjectIds order
  const orderedSelectedProjects = selectedProjectIds
    .map((id) => selectedProjects.find((p) => p.id === id))
    .filter((p): p is Project => p !== undefined)

  // Available projects (not selected)
  const availableProjects = projects.filter((p) => !selectedProjectIds.includes(p.id))

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <label className="block text-sm font-medium text-gray-700">
          Selected Projects ({selectedProjectIds.length}/{limit})
        </label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? 'Close' : 'Select Projects'}
        </Button>
      </div>

      {/* Selected Projects List */}
      {orderedSelectedProjects.length > 0 && (
        <div className="space-y-2">
          {orderedSelectedProjects.map((project, index) => {
            const title = project.i18n[0]?.title || project.slug
            return (
              <div
                key={project.id}
                className="flex items-center gap-2 p-3 bg-gray-50 rounded border"
              >
                <GripVertical className="w-4 h-4 text-gray-400 cursor-move" />
                {project.coverMedia && (
                  <img
                    src={adminMediaFileUrl(project.coverMedia.id)}
                    alt={title}
                    className="w-12 h-12 object-cover rounded"
                  />
                )}
                <div className="flex-1">
                  <p className="text-sm font-medium">{title}</p>
                  <p className="text-xs text-gray-500">{project.slug}</p>
                </div>
                <div className="flex items-center gap-2">
                  {index > 0 && (
                    <button
                      type="button"
                      onClick={() => handleMoveProject(index, index - 1)}
                      className="text-gray-400 hover:text-gray-600"
                      title="Move up"
                    >
                      ↑
                    </button>
                  )}
                  {index < orderedSelectedProjects.length - 1 && (
                    <button
                      type="button"
                      onClick={() => handleMoveProject(index, index + 1)}
                      className="text-gray-400 hover:text-gray-600"
                      title="Move down"
                    >
                      ↓
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleRemoveProject(project.id)}
                    className="text-red-400 hover:text-red-600"
                    title="Remove"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Project Selection Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-xl font-semibold">Select Projects</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Search */}
            <div className="p-4 border-b">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Projects Grid */}
            <div className="flex-1 overflow-y-auto p-4">
              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : availableProjects.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  {searchQuery ? 'No projects found.' : 'No available projects.'}
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {availableProjects.map((project) => {
                    const title = project.i18n[0]?.title || project.slug
                    const isSelected = selectedProjectIds.includes(project.id)
                    const isDisabled = !isSelected && selectedProjectIds.length >= limit

                    return (
                      <div
                        key={project.id}
                        className={`relative border-2 rounded-lg overflow-hidden cursor-pointer transition-all ${
                          isSelected
                            ? 'border-indigo-600 ring-2 ring-indigo-200'
                            : isDisabled
                            ? 'border-gray-200 opacity-50 cursor-not-allowed'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                        onClick={() => !isDisabled && handleSelectProject(project.id)}
                      >
                        {project.coverMedia ? (
                          <img
                            src={adminMediaFileUrl(project.coverMedia.id)}
                            alt={title}
                            className="w-full h-32 object-cover"
                          />
                        ) : (
                          <div className="w-full h-32 bg-gray-100 flex items-center justify-center">
                            <span className="text-gray-400 text-sm">No cover</span>
                          </div>
                        )}
                        <div className="p-2 bg-white">
                          <p className="text-xs font-medium truncate">{title}</p>
                          <p className="text-xs text-gray-500 truncate">{project.slug}</p>
                        </div>
                        {isSelected && (
                          <div className="absolute top-2 right-2 bg-indigo-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs">
                            ✓
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t flex justify-end">
              <Button onClick={() => setIsOpen(false)}>Done</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

