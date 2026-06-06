'use client'

import { useCallback, useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import {
  Upload,
  Search,
  Copy,
  Trash2,
  Image as ImageIcon,
  Loader2,
  FileText,
  Video,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { adminMediaFileUrl } from '@/lib/admin/adminMediaFileUrl'

interface Media {
  id: string
  key: string
  url: string
  /** URL publique stockée (préférable pour « Copy URL ») */
  publicUrl?: string
  filename: string
  mimeType: string
  size: number
  width: number | null
  height: number | null
  alt: string | null
  createdAt: string
  uploadedBy: {
    id: string
    email: string
  } | null
}

interface MediaFacets {
  all: number
  images: number
  videos: number
  documents: number
}

type MediaTab = 'all' | 'images' | 'videos' | 'documents'

const PAGE_SIZE_OPTIONS = [48, 96, 144] as const

const TAB_TO_TYPE: Record<MediaTab, string | null> = {
  all: null,
  images: 'image',
  videos: 'video',
  documents: 'document',
}

export default function AdminMediaPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [media, setMedia] = useState<Media[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<MediaTab>('all')
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState<number>(PAGE_SIZE_OPTIONS[0])
  const [total, setTotal] = useState(0)
  const [facets, setFacets] = useState<MediaFacets>({
    all: 0,
    images: 0,
    videos: 0,
    documents: 0,
  })

  const fetchMedia = useCallback(async () => {
    setLoading(true)
    setError(null)
    const ac = new AbortController()
    const t = setTimeout(() => ac.abort(), 45_000)
    try {
      const params = new URLSearchParams()
      params.set('limit', String(pageSize))
      params.set('offset', String(page * pageSize))
      if (search.trim()) params.set('search', search.trim())
      const type = TAB_TO_TYPE[activeTab]
      if (type) params.set('type', type)

      const response = await fetch(`/api/admin/media?${params.toString()}`, {
        credentials: 'include',
        signal: ac.signal,
      })
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch media')
      }
      const data = await response.json()
      setMedia(data.media || [])
      setTotal(data.pagination?.total ?? 0)
      if (data.facets) {
        setFacets(data.facets)
      }
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        setError('Délai dépassé : vérifie que Next.js tourne et que la base répond.')
      } else {
        setError(e.message || 'Failed to load media')
      }
    } finally {
      clearTimeout(t)
      setLoading(false)
    }
  }, [activeTab, page, pageSize, router, search])

  useEffect(() => {
    fetchMedia()
  }, [fetchMedia])

  const handleTabChange = (tab: MediaTab) => {
    setActiveTab(tab)
    setPage(0)
  }

  const handlePageSizeChange = (size: number) => {
    setPageSize(size)
    setPage(0)
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/admin/media/upload', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.error || `Upload failed: ${response.status} ${response.statusText}`)
      }

      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }

      setPage(0)
      await fetchMedia()
    } catch (e: any) {
      console.error('Upload error:', e)
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
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Delete failed')
      }

      await fetchMedia()
    } catch (e: any) {
      setError(e.message || 'Delete failed')
    }
  }

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url)
    setCopiedUrl(url)
    setTimeout(() => setCopiedUrl(null), 2000)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getMediaType = (mimeType: string): 'image' | 'video' | 'document' => {
    if (mimeType.startsWith('image/')) return 'image'
    if (mimeType.startsWith('video/')) return 'video'
    return 'document'
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const rangeStart = total === 0 ? 0 : page * pageSize + 1
  const rangeEnd = Math.min(total, (page + 1) * pageSize)

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Media Library</h1>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelected}
            accept="image/*,application/pdf,video/mp4,video/webm"
            className="hidden"
            disabled={uploading}
          />
          <Button type="button" onClick={handleUploadClick} disabled={uploading}>
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                Upload Media
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => handleTabChange('all')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'all'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              All ({facets.all})
            </button>
            <button
              onClick={() => handleTabChange('images')}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === 'images'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <ImageIcon className="w-4 h-4" />
              Images ({facets.images})
            </button>
            <button
              onClick={() => handleTabChange('videos')}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === 'videos'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Video className="w-4 h-4" />
              Videos ({facets.videos})
            </button>
            <button
              onClick={() => handleTabChange('documents')}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === 'documents'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <FileText className="w-4 h-4" />
              Documents ({facets.documents})
            </button>
          </nav>
        </div>
      </div>

      {/* Search + page size */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-md flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Search media by filename or alt text..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(0)
            }}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-600 shrink-0">
          Par page
          <select
            value={pageSize}
            onChange={(e) => handlePageSizeChange(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            {PAGE_SIZE_OPTIONS.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-800 rounded-md flex items-center justify-between">
          <span>Error: {error}</span>
          <button onClick={() => setError(null)} className="text-red-600 hover:text-red-800 ml-4">
            ×
          </button>
        </div>
      )}

      {/* Media Grid */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading media...</div>
      ) : media.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          {activeTab === 'images' && <ImageIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />}
          {activeTab === 'videos' && <Video className="w-12 h-12 text-gray-400 mx-auto mb-4" />}
          {activeTab === 'documents' && <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />}
          {activeTab === 'all' && <ImageIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />}
          <p className="text-gray-600 mb-2">No {activeTab === 'all' ? 'media' : activeTab} found</p>
          <p className="text-sm text-gray-500">
            {search ? 'Try a different search term.' : 'Upload your first file to get started.'}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-7 xl:grid-cols-8 gap-2">
            {media.map((item) => {
              const mediaType = getMediaType(item.mimeType)
              const isImage = mediaType === 'image'
              const isDocument = mediaType === 'document'

              return (
                <div
                  key={item.id}
                  className="group bg-white border border-gray-200 rounded-md overflow-hidden hover:shadow-md hover:border-gray-300 transition-all"
                >
                  {isImage ? (
                    <img
                      src={adminMediaFileUrl(item.id)}
                      alt={item.alt || item.filename}
                      loading="lazy"
                      className="w-full h-20 object-cover bg-gray-100"
                    />
                  ) : mediaType === 'video' ? (
                    <div className="w-full h-20 bg-gray-900 flex items-center justify-center relative">
                      <Video className="w-6 h-6 text-white/80" />
                    </div>
                  ) : isDocument ? (
                    <div className="w-full h-20 bg-gray-50 flex flex-col items-center justify-center border-b border-gray-100">
                      <FileText className="w-7 h-7 text-red-600" />
                      <a
                        href={adminMediaFileUrl(item.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-0.5 text-[10px] text-indigo-600 hover:text-indigo-800 underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        PDF
                      </a>
                    </div>
                  ) : (
                    <div className="w-full h-20 bg-gray-100 flex items-center justify-center">
                      <FileText className="w-6 h-6 text-gray-400" />
                    </div>
                  )}
                  <div className="p-1.5">
                    <p className="text-[11px] font-medium text-gray-900 truncate" title={item.filename}>
                      {item.filename}
                    </p>
                    <p className="text-[10px] text-gray-500 truncate">
                      {formatFileSize(item.size)}
                      {item.width && item.height ? ` · ${item.width}×${item.height}` : ''}
                    </p>
                    <div className="mt-1 flex gap-1">
                      <button
                        onClick={() => handleCopyUrl(item.publicUrl ?? item.url)}
                        className="flex-1 text-[10px] px-1 py-0.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center justify-center"
                        title="Copy URL"
                      >
                        <Copy className="w-3 h-3" />
                        <span className="ml-0.5 truncate">
                          {copiedUrl === (item.publicUrl ?? item.url) ? 'OK' : 'URL'}
                        </span>
                      </button>
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="px-1 py-0.5 text-red-600 hover:bg-red-50 rounded"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="mt-6 flex flex-col gap-3 border-t border-gray-200 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-gray-600">
              {total === 0
                ? 'Aucun média'
                : `Affichage ${rangeStart}–${rangeEnd} sur ${total} média${total > 1 ? 's' : ''} — page ${page + 1} / ${totalPages}`}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 0 || loading}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
                Précédent
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page + 1 >= totalPages || loading}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
