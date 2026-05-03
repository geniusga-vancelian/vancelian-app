'use client'

import { useEffect, useState } from 'react'
import { X, Upload, Search, Copy, Trash2, Image as ImageIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { adminMediaFileUrl } from '@/lib/admin/adminMediaFileUrl'

interface Media {
  id: string
  key: string
  url: string
  publicUrl?: string
  filename: string
  mimeType: string
  size: number
  width: number | null
  height: number | null
  alt: string | null
  createdAt: string
}

interface MediaPickerProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (media: Media) => void
  currentMediaId?: string | null
  title?: string
}

export function MediaPicker({
  isOpen,
  onClose,
  onSelect,
  currentMediaId,
  title = 'Select Media',
}: MediaPickerProps) {
  const [media, setMedia] = useState<Media[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      fetchMedia()
    }
  }, [isOpen, search])

  const fetchMedia = async () => {
    setLoading(true)
    setError(null)
    try {
      const url = search
        ? `/api/admin/media?search=${encodeURIComponent(search)}`
        : '/api/admin/media'
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error('Failed to fetch media')
      }
      const data = await response.json()
      setMedia(data.media || [])
    } catch (e: any) {
      setError(e.message || 'Failed to load media')
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/admin/media/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Upload failed')
      }

      const data = await response.json()
      await fetchMedia() // Refresh list
      e.target.value = '' // Reset input
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (mediaId: string) => {
    if (!confirm('Are you sure you want to delete this media?')) {
      return
    }

    try {
      const response = await fetch(`/api/admin/media/${mediaId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Delete failed')
      }

      await fetchMedia() // Refresh list
    } catch (e: any) {
      setError(e.message || 'Delete failed')
    }
  }

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url)
    // Could add a toast notification here
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search and Upload */}
        <div className="p-4 border-b space-y-3">
          <div className="flex items-center space-x-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search media..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <label className="cursor-pointer">
              <input
                type="file"
                onChange={handleUpload}
                accept="image/*,application/pdf,video/mp4,video/webm"
                className="hidden"
                disabled={uploading}
              />
              <Button type="button" disabled={uploading}>
                <Upload className="w-4 h-4 mr-2" />
                {uploading ? 'Uploading...' : 'Upload'}
              </Button>
            </label>
          </div>
          {error && (
            <div className="text-red-600 text-sm bg-red-50 p-2 rounded">
              {error}
            </div>
          )}
        </div>

        {/* Media Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : media.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No media found. Upload a file to get started.
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {media.map((item) => {
                const isImage = item.mimeType.startsWith('image/')
                const isSelected = item.id === currentMediaId

                return (
                  <div
                    key={item.id}
                    className={`relative border-2 rounded-lg overflow-hidden cursor-pointer transition-all ${
                      isSelected
                        ? 'border-indigo-600 ring-2 ring-indigo-200'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => onSelect(item)}
                  >
                    {isImage ? (
                      <img
                        src={adminMediaFileUrl(item.id)}
                        alt={item.alt || item.filename}
                        className="w-full h-32 object-cover"
                      />
                    ) : (
                      <div className="w-full h-32 bg-gray-100 flex items-center justify-center">
                        <ImageIcon className="w-8 h-8 text-gray-400" />
                      </div>
                    )}
                    <div className="p-2 bg-white">
                      <p className="text-xs font-medium truncate">{item.filename}</p>
                      <p className="text-xs text-gray-500">{formatFileSize(item.size)}</p>
                    </div>
                    <div className="absolute top-2 right-2 flex space-x-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleCopyUrl(item.publicUrl ?? item.url)
                        }}
                        className="bg-white/90 hover:bg-white p-1 rounded"
                        title="Copy URL"
                      >
                        <Copy className="w-3 h-3 text-gray-600" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(item.id)
                        }}
                        className="bg-white/90 hover:bg-white p-1 rounded text-red-600"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t flex justify-end">
          <Button onClick={onClose} variant="outline">
            Cancel
          </Button>
        </div>
      </div>
    </div>
  )
}









